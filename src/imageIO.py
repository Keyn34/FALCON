#!/usr/bin/env python
# -*- coding: utf-8 -*-


# **********************************************************************************************************************
# File: imageIO.py
# Project: falcon
# Created: 27.01.2022
# Author: Lalith Kumar Shiyam Sundar
# Email: lalith.shiyamsundar@meduniwien.ac.at
# Institute: Quantitative Imaging and Medical Physics, Medical University of Vienna
# Description: Falcon (FALCON) is a tool for the performing dynamic PET motion correction. It is based on the greedy
# algorithm developed by the Paul Yushkevich. The algorithm is capable of performing fast rigid/affine/deformable
# registration.
# License: Apache 2.0
# **********************************************************************************************************************


import logging
import os
import pathlib
import re
import subprocess
import sys

import SimpleITK as sitk
import nibabel as nib
import numpy as np
import pydicom as dicom
from halo import Halo
from tqdm import tqdm

import fileOp as fop


def check_unique_extensions(directory: str) -> list:
    """Check the number of unique file extensions in a directory by getting all the file extensions
    :param directory: Directory to check
    :return: Identified unique file extensions
    """
    extensions = []
    for file in os.listdir(directory):
        if file.endswith(".nii") or file.endswith(".nii.gz"):
            extensions.append(".nii")
        elif file.endswith(".DCM") or file.endswith(".dcm"):
            extensions.append(".dcm")
        elif file.endswith(".IMA") or file.endswith(".ima"):
            extensions.append(".ima")
        elif file.endswith(".hdr") or file.endswith('.img'):
            extensions.append(".hdr")
        elif file.endswith(".mha"):
            extensions.append(".mha")
        else:
            extensions.append("unknown")
    extensions_set = set(extensions)
    unique_extensions = list(extensions_set)
    return unique_extensions


def check_image_type(file_extension: str) -> str:
    """Check if a given extension is nifti, dicom, analyze or metaimage in a given directory
    :param file_extension: File extension to check
    :return: Image type
    """
    if file_extension == ".nii":
        return "Nifti"
    elif file_extension == ".dcm" or file_extension == ".ima":
        return "Dicom"
    elif file_extension == ".hdr":
        return "Analyze"
    elif file_extension == ".mha":
        return "Metaimage"
    else:
        return "Unknown"


def nondcm2nii(medimg_dir: str, file_extension: str, new_dir: str) -> None:
    """Convert non-DICOM images to NIFTI
    :param medimg_dir: Directory containing the non-DICOM images (e.g. Analyze, Metaimage)
    :param file_extension: File extension of the non-DICOM images (e.g. .hdr, .mha)
    :param new_dir: Directory to save the converted images
    """
    non_dcm_files = fop.get_files(medimg_dir, wildcard='*' + file_extension)
    for file in non_dcm_files:
        file_stem = pathlib.Path(file).stem
        nifti_file = os.path.join(new_dir, file_stem + ".nii.gz")
        cmd_to_run = f"c3d {file} -o {nifti_file}"
        logging.info(f"Converting {file} to {nifti_file}")
        spinner = Halo(text=f"Running command: {cmd_to_run}", spinner='dots')
        spinner.start()
        os.system(cmd_to_run)
        spinner.succeed()
        logging.info("Done")


def dcm2nii(dicom_dir: str) -> None:
    """Convert DICOM images to NIFTI using dcm2niix
    :param dicom_dir: Directory containing the DICOM images
    """
    cmd_to_run = f"dcm2niix {re.escape(dicom_dir)}"
    logging.info(f"Converting DICOM images in {dicom_dir} to NIFTI")
    spinner = Halo(text=f"Converting DICOM images in {dicom_dir} to NIFTI", spinner='dots')
    spinner.start()
    subprocess.run(cmd_to_run, shell=True, capture_output=True)
    spinner.succeed()
    logging.info("Done")


def split4d(nifti_file: str, out_dir: str) -> None:
    """Split a 4D NIFTI file into 3D NIFTI files using nibabel
    :param nifti_file: 4D NIFTI file to split
    :param out_dir: Directory to save the split NIFTI files
    """
    logging.info(f"Splitting {nifti_file} into 3D nifti files")
    spinner = Halo(text=f"Splitting {nifti_file} into 3D nifti files", spinner='dots')
    spinner.start()
    split_nifti_files = nib.funcs.four_to_three(nib.funcs.squeeze_image(nib.load(nifti_file)))
    i = 0
    for file in split_nifti_files:
        nib.save(file, os.path.join(out_dir, 'vol' + str(i).zfill(4) + '.nii.gz'))
        i += 1
    logging.info(f"Splitting done and split files are saved in {out_dir}")
    spinner.succeed()


def merge3d(nifti_dir: str, wild_card: str, nifti_outfile: str) -> None:
    """
    Merge 3D NIFTI files into a 4D NIFTI file using nibabel
    :param nifti_dir: Directory containing the 3D NIFTI files
    :param wild_card: Wildcard to use to find the 3D NIFTI files
    :param nifti_outfile: User-defined output file name for the 4D NIFTI file
    """
    logging.info(f"Merging 3D nifti files in {nifti_dir} with wildcard {wild_card}")
    files_to_merge = fop.get_files(nifti_dir, wild_card)
    nib.save(nib.funcs.concat_images(files_to_merge, False), nifti_outfile)
    os.chdir(nifti_dir)
    logging.info("Done")


def convert_all_non_nifti(medimg_dir: str):
    """Convert all non-nifti files to nifti
    :param medimg_dir: Directory containing the non-nifti files
    :return: A tuple containing the Directory that contains the converted nifti files and the original image type
    """

    # Getting unique extensions in a given folder to check if the folder has multiple image formats

    nifti_dir = ''
    image_type = ''
    unique_extensions = check_unique_extensions(
        directory=medimg_dir)

    # If the folder has multiple image formats, conversion is a hassle. Therefore, throw an error to clean up the given
    # directory

    if len(unique_extensions) > 1:
        logging.error(f"Multiple file formats found: {unique_extensions} - please check the "
                      f"directory!")
        sys.exit(f"Multiple file formats found: {unique_extensions} - please check the directory!")

    # If the folder has only one unique image format (e.g, dicom, nifti, analyze, metaimage), convert the non-nifti
    # files to nifti files

    elif len(unique_extensions) == 1:
        logging.info(f"Found files with following extension: {unique_extensions[0]}")
        image_type = check_image_type(*unique_extensions)
        logging.info(f"Image type: {image_type}")
        if image_type == 'Dicom':  # if the image type is dicom, convert the dicom files to nifti files
            nifti_dir = fop.make_dir(medimg_dir, 'nifti')
            dcm2nii(dicom_dir=medimg_dir)
            fop.move_files(medimg_dir, nifti_dir, '*.nii*')
        elif image_type == 'Nifti':  # do nothing if the files are already in nifti
            logging.info('Files are already in nifti format!')
            nifti_dir = medimg_dir
        else:  # any other format (analyze or metaimage) convert to nifti
            nifti_dir = fop.make_dir(medimg_dir, 'nifti')
            nondcm2nii(medimg_dir=medimg_dir, file_extension=unique_extensions[0], new_dir=nifti_dir)

    return nifti_dir, image_type


def nii2nondcm(nifti_file=str, new_img_type=str, new_dir=str) -> None:
    """
    Convert nifti to non-dicom format (e.g, analyze, metaimage)
    :param nifti_file: path of the NIFTI file to convert
    :param new_img_type: File extension to use for the converted file
    :param new_dir: Directory to save the converted file
    """
    logging.info(f"Converting {nifti_file} to {new_img_type} format")
    file_stem = pathlib.Path(nifti_file).stem
    new_img_file = os.path.join(new_dir, file_stem + new_img_type)
    cmd_to_run = f"c3d {nifti_file} -o {new_img_file}"
    logging.info(f"Running command: {cmd_to_run}")
    os.system(cmd_to_run)
    logging.info("Done")


def nii2dcm(nifti_file=str) -> None:
    """
    Convert nifti to dicom format
    :param nifti_file: path of the NIFTI file to convert
    :return dicom_dir: Directory containing the converted dicom files
    """
    logging.info(f"Converting {nifti_file} to dicom format")
    cmd_to_run = f"nii2dcm {nifti_file}"
    logging.info(f"Running command: {cmd_to_run}")
    print("Dicom conversion may take a while. Please wait...")
    os.system(cmd_to_run)
    print("Done, Dicom files (dir name = dcm_files) are saved in the same directory as the NIFTI file")
    logging.info("Done, Dicom files (dir name = dcm_files) are saved in the same directory as the NIFTI file")


def revert_nifti_to_original_fmt(nifti_file=str, org_image_fmt=str, new_dir=str) -> None:
    """
    Revert nifti images to original file format
    :param nifti_file: Nifti file to revert
    :param org_image_fmt: Original image format
    :param new_dir: Directory containing the converted files
    """
    logging.info(f"Reverting {nifti_file} to {org_image_fmt} format")
    if org_image_fmt == 'Dicom':
        nii2dcm(nifti_file=nifti_file)
    elif org_image_fmt == 'Nifti':
        logging.info('Files are already in nifti format!')
    else:
        logging.info(f"Converting {nifti_file} to {org_image_fmt} format")
        nii2nondcm(nifti_file=nifti_file, new_img_type=org_image_fmt, new_dir=new_dir)


def push_nii_pixel_data_to_dcm(nifti_file: str, dicom_dir: str, out_dir: str) -> str:
    """
    Pushes the pixel data from a nifti file to the DICOM files in a directory. The DICOM tags are preserved while the
    pixel data is replaced.
    :param nifti_file: Path to the nifti file
    :param dicom_dir: Path to the directory containing DICOM files
    :param out_dir: Path to the output directory
    :return out_dir: Path to the output directory
    """
    print("Reading nifti file as int16...")
    nii_img = sitk.ReadImage(nifti_file, sitk.sitkInt16)
    print("Flipping the nifti image to match the dicom orientation...")
    nii_img = sitk.Flip(nii_img, [True, True, True])
    nii_array = sitk.GetArrayFromImage(nii_img)
    dicom_files = fop.get_files(dicom_dir, "*.dcm")
    # if dicom_files empty use different wildcard
    if not dicom_files:
        dicom_files = fop.get_files(dicom_dir, "*.IMA")
    if np.shape(nii_array)[0] != len(dicom_files):
        raise Exception("Number of slices in nifti file and dicom directory do not match")

    counter = 0
    for dicom_file in tqdm(dicom_files):
        dcm = dicom.read_file(dicom_file)
        dicom_file_name = pathlib.Path(dicom_file).name
        # inverse rescale slope and intercept
        nii_array[counter, :, :] = np.subtract(nii_array[counter, :, :], int(dcm.RescaleIntercept))
        nii_array[counter, :, :] = np.divide(nii_array[counter, :, :], int(dcm.RescaleSlope))
        # push pixel data to dicom file as int16 stream
        dcm['PixelData'].VR = 'OW'
        dcm.PixelData = nii_array[counter, :, :].astype('uint16').tobytes()
        dcm.save_as(os.path.join(out_dir, dicom_file_name))
        counter += 1

    print("Pushing pixel data to dicom files complete!")
    print("Output DICOM directory: " + out_dir)

    return out_dir
