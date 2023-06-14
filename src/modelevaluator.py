"""
This class evaluates a generic binary classification model.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mlxtend.plotting import plot_confusion_matrix
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    confusion_matrix,
    roc_curve,
    precision_recall_curve,
    f1_score,
    precision_score,
    recall_score,
)

class ModelEvaluator:

    def __init__(self, model_name, y_true, y_proba, threshold=0.5):
        self.model_name = model_name
        self.y_true = y_true
        self.y_proba = y_proba
        self.threshold = threshold
        self.y_pred = np.where(y_proba > self.threshold, 1, 0)

    def evaluate_metrics(self):

        # Calculate accuracy
        accuracy = accuracy_score(self.y_true, self.y_pred)
        print("Accuracy: ", accuracy)

        # Calculate AUC
        auc = roc_auc_score(self.y_true, self.y_proba)
        print("AUC: ", auc)

        # Calculate precision
        precision = precision_score(self.y_true, self.y_pred)
        print("Precision: ", precision)

        # Calculate recall
        recall = recall_score(self.y_true, self.y_pred)
        print("Recall: ", recall)

        # Calculate F1 score
        f1 = f1_score(self.y_true, self.y_pred)
        print("F1 score: ", f1)

        # Calculate specificity
        specificity = specificity_score(self.y_true, self.y_pred)
        print("Specificity: ", specificity)

    def plot_roc_curve(self):

        # Calculate ROC curve
        fpr, tpr, thresholds = roc_curve(self.y_true, self.y_proba)

        # Calculate AUC
        auc = roc_auc_score(self.y_true, self.y_proba)

        # Plot ROC curve
        fig, ax = plt.subplots(figsize=(10, 10))

        ax.plot(fpr, tpr, label=f"{self.model_name} (AUC = {auc:.2f})")
        ax.plot([0, 1], [0, 1], linestyle='--', label='Random Classifier')
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title(f"{self.model_name} ROC Curve")
        ax.legend(loc='lower right')
        plt.show()

    def plot_confusion_matrix(self):

        # Calculate confusion matrix
        fig, ax = plt.subplots(figsize=(10, 10))
        cm = confusion_matrix(self.y_true, self.y_pred)
        ax.set_title(f"{self.model_name} Confusion Matrix")
        plot_confusion_matrix(conf_mat=cm,
                              show_absolute=True,
                              show_normed=True,
                              colorbar=True, figure=fig, axis=ax)

        ax.set_xlabel('Predicted label')
        ax.set_ylabel('True label')
        plt.show()
    
    def plot_precision_recall_curve(self):
        
        # Calculate precision-recall curve
        precision, recall, thresholds = precision_recall_curve(self.y_true, self.y_proba)
        
        # Plot precision-recall curve
        fig, ax = plt.subplots(figsize=(10, 10))
        
        ax.plot(recall, precision, label=f"{self.model_name}")
        ax.set_xlabel('Recall')
        ax.set_ylabel('Precision')
        ax.set_title(f"{self.model_name} Precision-Recall Curve")
        ax.legend(loc='lower right')
        plt.show()
