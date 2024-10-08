"""
Contains functions to load data in an organized manner.
"""

import os
import os.path

# import numpy
import pickle
from glob import glob

import numpy as np

import torch
from torch.utils.data import Dataset, DataLoader

from transformations.base import BaseTransformation

# from transformations.positions_to_displacements import PositionToDisplacement

# number of sequences in each dataset
# train:205942  val:3200 test: 36272
# sequences sampled at 10HZ rate


class ArgoverseDataset(Dataset):
    """Dataset class for Argoverse"""

    def __init__(self, data_path: str, transform=None):
        """TODO: init"""
        super(ArgoverseDataset, self).__init__()
        self.data_path = data_path
        self.transform = transform

        self.pkl_list = glob(os.path.join(self.data_path, "*"))
        self.pkl_list.sort()

    def __len__(self):
        """TODO: len"""
        return len(self.pkl_list)

    def __getitem__(self, idx):
        """getitem"""
        pkl_path = self.pkl_list[idx]
        with open(pkl_path, "rb") as f:
            data = pickle.load(f)

        if self.transform:
            data = self.transform(data)

        return data


def collate(batch_data):
    """
    Apply the collate transformation to the given batch_data.

    Args:
        batch_data (list): List of dictionaries representing the batch data.

    Returns:
        Tensor: Transformed batch data, ready for input to the model.
    """

    batch_inputs = []
    batch_labels = []
    batch_prediction_correction = []
    batch_correction_metadata = []

    for datum in batch_data:
        model_input, label, prediction_correction, metadata = datum

        batch_inputs.append(model_input)
        batch_labels.append(label)
        batch_prediction_correction.append(prediction_correction)
        batch_correction_metadata.append(metadata)

    # print(batch_inputs)

    inputs = np.array(batch_inputs)
    labels = np.array(batch_labels)

    # we only need one function reference because all data should have
    # the same correction function
    prediction_correction = batch_prediction_correction[0]

    inputs = torch.tensor(inputs, dtype=torch.float32)

    # TODO device
    inputs.to("cpu")

    # TODO convert to tensors

    # convert all inputs to tensors
    inputs = tuple(inputs)

    # convert all labels to tensors
    labels = torch.tensor(labels, dtype=torch.float32)

    return inputs, labels, prediction_correction, batch_correction_metadata


def create_data_loader(model_config, data_config, train=True, examine=False):
    """TODO: create_data_loader"""
    #   data_path: str, transforms=None, batch_size=4, shuffle=False, val_split=0.0, num_workers=1
    if train:
        data_path = data_config["train_path"]
    else:
        data_path = data_config["val_path"]

    # extract params
    batch_size = data_config["batch_size"]
    num_workers = data_config["num_workers"]
    train_val_split = data_config["train_val_split"]

    # create the transformation function
    transform_function = BaseTransformation(model_config, data_config)

    # create the dataset
    dataset = ArgoverseDataset(
        data_path,
        transform=transform_function,
    )

    # use random_split to get the training and validation sets
    train_split = train_val_split
    val_split = 1 - train_val_split

    train_set, val_set = torch.utils.data.random_split(
        dataset, [train_split, val_split]
    )

    train_loader = DataLoader(
        train_set,
        shuffle=False,
        batch_size=batch_size,
        collate_fn=collate,
        num_workers=num_workers,
        multiprocessing_context="spawn",
    )

    val_loader = DataLoader(
        val_set,
        batch_size=batch_size,
        collate_fn=collate,
        num_workers=num_workers,
        multiprocessing_context="spawn",
    )

    return train_loader, val_loader
