import torch
import torch.nn as nn
from models.mobilenetv2 import (
    get_model as get_model_mobilenetv2
)
from models.mobilenet import (
    get_model as get_model_mobilenet
)
from models.squeezenet import (
    get_model as get_model_squeezenet
)

def build_model(base_model_path, type='mobilenet', gpus=None, width_mult=1.):
    # All models pretrained on Jester (27 classes)
    if type == 'mobilenet':
        model=get_model_mobilenet(num_classes=27, sample_size = 224, width_mult=width_mult)
    elif type=='mobilenetv2':
        model=get_model_mobilenetv2(num_classes=27, sample_size = 224, width_mult=width_mult)
    elif type=='squeezenet':
        model=get_model_squeezenet(sample_size=224, sample_duration=16, num_classes=27)
    else:
        print("Unknown model type. Select between: mobilenet, mobilenetv2, squeezenet.")
        return None
        
    model=model.cuda()
    model=nn.DataParallel(model, device_ids=gpus)
    checkpoint=torch.load(base_model_path)
    model.load_state_dict(checkpoint['state_dict'])

    # Freeze model weights
    for param in list(model.parameters()):
        param.requires_grad = False

    classifier = model.module.get_submodule('classifier')
    print(f"Previous classifier: {classifier}")

    if type == 'squeezenet': # Version 1.0 or 1.1
        # Weights of the new classifier will be fine-tunable
        last_duration = model.module.last_duration
        last_size = model.module.last_size
        new_classifier = nn.Sequential(
            nn.Dropout(p=0.5),
            nn.Conv3d(512, 2, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.AvgPool3d((last_duration, last_size, last_size), stride=1)
        )
        torch.nn.init.kaiming_normal_(new_classifier[1].weight, mode='fan_out')
    else:
        new_classifier = nn.Sequential(
            nn.Dropout(p=0.5, inplace=False),
            nn.Linear(in_features=model.module.last_channel, out_features=2, bias=True)
        )

    # Init weights of the linear layer
    # nn.init.normal_(tensor=new_classifier[1].weight, mean=0.0, std=1.0)

    new_classifier.cuda()
    model.module.classifier = new_classifier
    classifier = model.module.get_submodule('classifier')
    print(f"New classifier: {classifier}")
    print("New model built successfully")

    x = torch.randn((2, 3, 16, 224, 224))
    out = model(x)
    print(out.shape)
    return model

if __name__ == '__main__':
    # build_model(base_model_path='models/pretrained/jester/jester_mobilenet_1.0x_RGB_16_best.pth')
    # build_model(base_model_path='models/pretrained/jester/jester_mobilenetv2_1.0x_RGB_16_best.pth', type="mobilenetv2")
    build_model(base_model_path='models/pretrained/jester/jester_squeezenet_RGB_16_best.pth', type='squeezenet')