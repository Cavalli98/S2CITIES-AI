import os
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, random_split
from data.Jester.jesterdataset.jester_dataset import JesterDataset
from build_models import build_model
import numpy as np
import functools
from tqdm import tqdm
from train_args import parse_args
from torchvideotransforms.volume_transforms import ClipToTensor
from torchvideotransforms.video_transforms import Compose, RandomHorizontalFlip, Resize

# Using wanbd (Weights and Biases, https://wandb.ai/) for run tracking
import wandb

# Silent warnings about TypedStorage deprecations that appear on the cluster
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='TypedStorage is deprecated')

args = parse_args()

def compute_video_accuracy(ground_truth, predictions, top_k=3):
    # Inspired by evaluation performed in Karpathy et al. CVPR14
    # Other evaluations are also possible

    # ground_truth: df with fields ['video-id', 'label']
    # predictions: df with fields ['video-id', 'label', 'score']
    # Takes the first top-k predicted labels (in ascending order), compare them with the ground-truth labels
    # and compute the average number of hits per video.
    # Number of hits = Number of steps in which one the top-k predicted labels is equal to the ground-truth.

    video_ids = np.unique(ground_truth['video-id'].values)
    avg_hits_per_video = np.zeros(video_ids.size)
    
    for i, video in enumerate(video_ids):
        pred_idx = predictions['video-id'] == video
        if not pred_idx.any():
            continue
        this_pred = predictions.loc[pred_idx].reset_index(drop=True)
        # Get top K predictions sorted by decreasing score.
        sort_idx = this_pred['score'].values.argsort()[::-1][:top_k]
        this_pred = this_pred.loc[sort_idx].reset_index(drop=True)
        # Get top K labels and compare them against ground truth.
        pred_label = this_pred['label'].tolist()
        gt_idx = ground_truth['video-id'] == video
        gt_label = ground_truth.loc[gt_idx]['label'].tolist()
        avg_hits_per_video[i] = np.mean([1 if this_label in pred_label else 0
                                         for this_label in gt_label])
        
    return float(avg_hits_per_video.mean())


# "Collate" function for our dataloaders
# def collate_fn(batch, transform):
#     # NOTE (IMPORTANT): Normalize (pytorchvideo.transforms) from PyTorchVideo wants a volume with shape CTHW, 
#     # which is then internally converted to TCHW, processed and then again converted to CTHW.
#     # Because our volumes are in the shape TCHW, we convert them to CTHW here, instead of doing it inside the training loop.

#     clips = [transform(video.permute(1, 0, 2, 3)) for video, _ in batch]
#     labels = [label for _, label in batch]

#     clips = torch.stack(clips)
#     labels = torch.tensor(labels)
#     return clips, labels

# TODO: Implement custom scheduler to manual adjust learning rate after N epochs
def train(model, optimizer, scheduler, criterion, train_loader, val_loader, num_epochs, device, pbar=None):

    # Set up early stopping criteria
    patience = args.early_stop_patience
    min_delta = 0.001  # Minimum change in validation loss to be considered as improvement
    best_loss = float('inf')  # Initialize the best validation loss
    best_accuracy = 0.0
    counter = 0  # Counter to keep track of epochs without improvement

    ############### Training ##################
    for epoch in range(num_epochs):
        model.train()

        epoch_loss = []
        corrects = 0
        totals = 0

        if pbar:
            pbar.set_description("[Epoch {}]".format(epoch))
            pbar.reset()

        for i, data in enumerate(train_loader):
            clips, labels = data
            clips = clips.float()
            clips = clips.to(device) # Send inputs to CUDA

            logits = model(clips)

            labels = labels.to(device)

            loss = criterion(logits, labels)
            epoch_loss.append(loss.item())

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            if pbar:
                pbar.update(clips.shape[0])

            y_preds = torch.argmax(torch.softmax(logits, dim=1), dim=1)

            corrects += (y_preds == labels).sum().item()
            totals += y_preds.shape[0]

        avg_train_loss = np.array(epoch_loss).mean()
        train_accuracy = 100 * corrects / totals

        print("[Epoch {}] Avg Loss: {}".format(epoch, avg_train_loss))
        print("[Epoch {}] Train Accuracy {:.2f}%".format(epoch, train_accuracy))

        # commit = false because I want commit to happen after validation (so that the step is incremented once per epoch)
        wandb.log({"train_accuracy": train_accuracy, "train_loss": avg_train_loss}, commit=False)

        # NOTE: test function validates the model when it takes in input the loader for the validation set
        val_accuracy, val_loss = test(loader=val_loader, model=model, criterion=criterion, output_features=output_features, device=device, epoch=epoch)
        scheduler.step(val_loss)

        # Checking early-stopping criteria
        if val_loss + min_delta < best_loss:
            best_loss = val_loss
            best_accuracy = val_accuracy
            counter = 0 # Reset the counter since there is improvement
            # Save the improved model
            torch.save(model.state_dict(),  os.path.join(args.model_save_path, f'best_model_{args.exp}.h5'))
        else:
            counter += 1 # Increment the counter, since there is no improvement

        # Check if training should be stopped 
        if counter >= patience:
            print(f"Early-stopping the training phase at epoch {epoch}")
            break
    
    print("--- END Training. Results - Best Val. Loss: {:.2f}, Best Val. Accuracy: {:.2f}".format(best_loss, best_accuracy))

def test(loader, model, criterion, device, epoch=None):
    totals = 0
    corrects = 0
    y_pred = []
    y_true = []
    val_loss = []

    with torch.no_grad():
        model.eval()

        for i, data in enumerate(loader):
            clips, labels = data
            clips = clips.float()
            clips = clips.to(device)

            logits = model(clips)

            # TODO: Extend evaluation to top-k rather than just top-1

            labels = labels.to(device)
            val_loss_batch = criterion(logits, labels)

            val_loss.append(val_loss_batch.item())

            y_true.append(labels)

            y_preds = torch.argmax(torch.softmax(logits, dim=1), dim=1)

            corrects += (y_preds == labels).sum().item()
            totals += y_preds.shape[0]

            y_preds = y_preds.detach().cpu()
            y_pred.append(y_preds)

    y_true = torch.cat(y_true, dim=0)
    y_pred = torch.cat(y_pred, dim=0)

    val_accuracy = 100 * corrects / totals
    val_loss = np.array(val_loss).mean()

    if epoch is not None:
        # Save metrics with wandb
        wandb.log({"val_accuracy": val_accuracy, "val_loss": val_loss}, commit=True)

        print('[Epoch {}] Validation Accuracy: {:.2f}%'.format(epoch, val_accuracy))
    else:
        wandb.log({"test_accuracy": val_accuracy, "test_loss": val_loss}, commit=True)

        print('Test Accuracy: {:.2f}%'.format(val_accuracy))

    return val_accuracy, val_loss

if __name__ == '__main__':

    batch_size=args.batch
    num_epochs=args.epochs

    # start a new wandb run to track this script
    wandb.init(
        # set the wandb project where this run will be logged
        project=args.wandb_project,
        entity=args.wandb_team,
        name=args.exp,  
        # track hyperparameters and run metadata
        config={
        "optimizer": args.optimizer,
        "lr": args.lr,
        "lr_patience": args.lr_patience,
        "momentum": args.momentum,
        "dampening": args.dampening if not args.nesterov else 0.,
        "nesterov": args.nesterov,
        "weight_decay": args.wd, 
        "architecture": args.model,
        "dataset": args.data_path.split("/")[-1],
        "epochs": num_epochs,
        "batch": batch_size,
        "frame_size": args.sample_size,
        "_duration": args.sample_duration,
        "early_stop_patience": args.early_stop_patience,
        "no_norm": args.no_norm
        }
    )

    clip_duration = args.sample_duration
    frame_size = args.sample_size

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print("Running on device {}".format(device))

    # TODO: Add options for random cropping and scaling for more experimenting with training on Jester

    train_clip_transform = Compose([
        RandomHorizontalFlip(),
        Resize(size=(frame_size, frame_size, 3)), # Resize any frame to shape (112, 112, 3) (H, W, C)
        # crop_method,
        ClipToTensor()
    ])

    # Initialize spatial and temporal transforms (validation versions)
    val_clip_transform = Compose([
        Resize(size=(frame_size, frame_size, 3)), # Resize any frame to shape (112, 112, 3) (H, W, C)
        ClipToTensor()
    ])

    # Initialize spatial and temporal transforms (test versions)
    # test_clip_transform = Compose([
    #     Resize(size=(frame_size, frame_size, 3)), # Resize any frame to shape (112, 112, 3) (H, W, C)
    #     ClipToTensor()
    # ])

    # Test again with Random Crops on clips from the test set.
    # NOTE: Pay attention - both in train, test and validation, Clip accuracy is computed, not Video accuracy.
    # To compute Video accuracy, we need to traverse the entire video while extracting clips and doing inference with our models.
    # Then, predicted logits should be averaged and the results after the softmax layer should be used to make a prediction 
    # for the entire video.
    # TODO: A good idea would be to plot the logits (better class predictions) produced at each step, and see how
    # they evolve during time. 

    # Load Train/Val/Test Jester splits (20bn-version)
    train_set = JesterDataset(csv_file='data/Jester/jester_data/Train.csv',
                              video_dir='data/Jester/jester_data/20bn-jester-v1/Train',
                              number_of_frames=clip_duration, 
                              video_transform=train_clip_transform)
    
    val_set = JesterDataset(csv_file='data/Jester/jester_data/Validation.csv',
                              video_dir='data/Jester/jester_data/20bn-jester-v1/Validation',
                              number_of_frames=clip_duration, 
                              video_transform=val_clip_transform)
    
    # test_set = JesterDataset(csv_file='data/Jester/jester_data/Test.csv',
    #                           video_dir='data/Jester/jester_data/20bn-jester-v1/Test',
    #                           number_of_frames=clip_duration, 
    #                           video_transform=test_clip_transform)
    
    # partial_collate_fn = functools.partial(collate_fn, transform=video_transforms)

    print('Size of Train Set: {}'.format(len(train_set)))
    print('Size of Validation Set: {}'.format(len(val_set)))
    # print('Size of Test Set: {}'.format(len(test_set)))

    num_gpus = torch.cuda.device_count()
    print(f"Available GPUs: {num_gpus}")

    # Initialize DataLoaders
    train_dataloader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=args.num_workers)
    val_dataloader = DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=args.num_workers)
    
    # test_dataloader = DataLoader(test_set, batch_size=batch_size, shuffle=False, num_workers=args.num_workers)

    num_classes = 27
    model = build_model(model_path=None, 
                        type=args.model,
                        num_classes=num_classes,
                        gpus=list(range(0, num_gpus)),
                        sample_size=args.sample_size,
                        sample_duration=args.sample_duration,
                        output_features=num_classes,
                        finetune=True)
    
    print(f"Model: {model}")
    print(f"Total parameters: {sum(p.numel() for p in model.parameters())}")
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print("Trainable parameters:", trainable_params)

    if args.nesterov:
        args.dampening = 0
    
    if args.optimizer == 'SGD':
        optimizer = torch.optim.SGD(list(model.parameters()), 
                                                    lr=args.lr, 
                                                    momentum=args.momentum, 
                                                    dampening=args.dampening,
                                                    weight_decay=args.wd,
                                                    nesterov=args.nesterov)
    elif args.optimizer == 'Adam':
        optimizer = torch.optim.Adam(list(model.parameters()), lr=args.lr, weight_decay=args.wd)

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer=optimizer, mode='min', patience=args.lr_patience, factor=0.1)
    
    criterion = nn.CrossEntropyLoss()

    # Initialize tqdm progress bar for tracking training steps
    pbar = tqdm(total=len(train_set))

    # Create model saves path if it doesn't exist yet
    if not os.path.exists(args.model_save_path):
        os.makedirs(args.model_save_path)

    train(model=model, 
          optimizer=optimizer,
          scheduler=scheduler,
          criterion=criterion, 
          train_loader=train_dataloader,
          val_loader=val_dataloader, 
          num_epochs=num_epochs,
          device=device, 
          pbar=pbar)

    # Load the best checkpoint obtained until now
    # best_checkpoint=torch.load(os.path.join(args.model_save_path, f'best_model_{args.exp}.h5'))
    # model.load_state_dict(best_checkpoint)
  
    # test(loader=test_dataloader, 
    #      model=model,
    #      criterion=criterion,
    #      device=device)
    
    # [optional] finish the wandb run, necessary in notebooks
    wandb.finish()