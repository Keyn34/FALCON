#!/usr/bin/env python
# -*- coding: utf-8 -*-


# ***********************************************************************************************************************
# File: imageOP.py
# Project: falcon
# Created: 27.01.2022
# Author: Lalith Kumar Shiyam Sundar
# Email: Lalith.Shiyamsundar@meduniwien.ac.at
# Institute: Quantitative Imaging and Medical Physics, Medical University of Vienna
# Description: Falcon (FALCON) is a tool for the performing dynamic PET motion correction. It is based on the greedy
# algorithm developed by the Paul Yushkevich. The algorithm is capable of performing fast rigid/affine/deformable
# registration.
# License: Apache 2.0
# **********************************************************************************************************************


# Imports
import subprocess
import SimpleITK
import nibabel
import pandas as pd
from nilearn.input_data import NiftiMasker


def sum_images_from_list(image_stack: list, summed_image_path: str = None) -> SimpleITK.Image:
    """
    Sums all images from a list of image paths
    :param image_stack: List of paths to images that should be summed
    :param summed_image_path: Optional path to the resulting, summed image
    :return: The summed image as SimpleITK.Image
    :rtype: SimpleITK.Image
    """
    # Start with the first image
    summed_image = SimpleITK.ReadImage(image_stack[0], SimpleITK.sitkFloat64)

    # Sum all other images
    for image_index in range(1, len(image_stack)):
        current_image = SimpleITK.ReadImage(image_stack[image_index], SimpleITK.sitkFloat64)
        summed_image = summed_image + current_image

    if summed_image_path is not None:
        SimpleITK.WriteImage(summed_image, summed_image_path)

    return summed_image


def create_mean_image_from_list(image_stack: list, mean_image_path: str = None) -> SimpleITK.Image:
    """
    Averages all images from a list of image paths
    :param image_stack: List of paths to images that should be averaged
    :param mean_image_path: Optional path to the resulting, mean image
    :return: The averaged image as SimpleITK.Image
    :rtype: SimpleITK.Image
    """
    mean_image = sum_images_from_list(image_stack) / len(image_stack)

    if mean_image_path is not None:
        SimpleITK.WriteImage(mean_image, mean_image_path)

    return mean_image


def get_dimensions(nifti_file: str) -> int:
    """
    Get the dimensions of a NIFTI image file
    :param nifti_file: NIFTI file to check
    """
    nifti_img = SimpleITK.ReadImage(nifti_file)
    img_dim = nifti_img.GetDimension()
    return img_dim


def get_pixel_id_type(nifti_file: str) -> str:
    """
    Get the pixel id type of a NIFTI image file
    :param nifti_file: NIFTI file to check
    """
    nifti_img = SimpleITK.ReadImage(nifti_file)
    pixel_id_type = nifti_img.GetPixelIDTypeAsString()
    return pixel_id_type


def get_intensity_statistics(nifti_file: str, multi_label_file: str) -> object:
    """
    Get the intensity statistics of a NIFTI image file
    :param nifti_file: NIFTI file to check
    :param multi_label_file: Multilabel file that is used to calculate the intensity statistics from nifti_file
    :return: stats_df, a dataframe with the intensity statistics
    """
    nifti_img = SimpleITK.ReadImage(nifti_file)
    multi_label_img = SimpleITK.ReadImage(multi_label_file)
    intensity_statistics = SimpleITK.LabelIntensityStatisticsImageFilter()
    intensity_statistics.Execute(multi_label_img, nifti_img)
    stats_list = [(intensity_statistics.GetMean(i), intensity_statistics.GetStandardDeviation(i),
                   intensity_statistics.GetMedian(i), intensity_statistics.GetMaximum(i),
                   intensity_statistics.GetMinimum(i)) for i in intensity_statistics.GetLabels()]
    columns = ['Mean', 'Standard Deviation', 'Median', 'Maximum', 'Minimum']
    stats_df = pd.DataFrame(data=stats_list, index=intensity_statistics.GetLabels(), columns=columns)
    return stats_df


def get_body_mask(nifti_file: str, mask_file: str) -> str:
    """
    Get time activity curves from a 4d nifti file
    :param nifti_file: 4d nifti file to get the time activity curves from
    :param mask_file: Name of the mask file that is derived from the 4d nifti file.
    :return: path of the mask file
    """
    nifti_masker = NiftiMasker(mask_strategy='epi', memory="nilearn_cache", memory_level=2, smoothing_fwhm=8)
    nifti_masker.fit(nifti_file)
    nibabel.save(nifti_masker.mask_img_, mask_file)
    return mask_file


def mask_img(nifti_file: str, mask_file: str, masked_file: str) -> str:
    """
    Mask a NIFTI image file with a mask file
    :param nifti_file: NIFTI file to mask
    :param mask_file: Mask file to mask the nifti_file with
    :param masked_file: Name of the masked file
    :return: path of the masked nifti file
    """
    img = SimpleITK.ReadImage(nifti_file)
    mask = SimpleITK.ReadImage(mask_file, SimpleITK.sitkFloat32)
    masked_img = SimpleITK.Compose(
        [SimpleITK.Multiply(SimpleITK.VectorIndexSelectionCast(img, i), mask) for i in
         range(img.GetNumberOfComponentsPerPixel())])
    SimpleITK.WriteImage(SimpleITK.Cast(masked_img, SimpleITK.sitkVectorFloat32), masked_file)
    return masked_file


def reslice_identity(reference_image: str, image_to_reslice: str, out_resliced_image: str, interpolation: str) -> None:
    """
    Reslice an image to the same space as another image
    :param reference_image: Path to the reference image to reslice to
    :param image_to_reslice: Path to the image to reslice
    :param out_resliced_image: Path to the resliced image
    :param interpolation: Interpolation method to use (NearestNeighbor, Linear, Cubic)
    """
    cmd_to_run = f"c3d {reference_image} {image_to_reslice} -interpolation {interpolation} -reslice-identity -o" \
                 f" {out_resliced_image}"
    subprocess.run(cmd_to_run, shell=True, capture_output=True)
