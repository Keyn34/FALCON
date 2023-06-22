#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# ***********************************************************************************************************************
# File: run_falcon_cardiac.py
# Project: falcon
# Created: 01.06.2023
# Author: Sebastian Gutschmayer
# Email: sebastian.gutschmayer@meduniwien.ac.at
# Institute: Quantitative Imaging and Medical Physics, Medical University of Vienna
# Description: Falcon (FALCON) is a tool for the performing dynamic PET motion correction. It is based on the greedy
# algorithm developed by Paul Yushkevich. The algorithm is capable of performing fast rigid/affine/deformable
# registration.
# License: Apache 2.0
# **********************************************************************************************************************


# Imports
import imageOp
import os
import subprocess
import fileOp
import argparse
import constants
from halo import Halo


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-rfd",
        "--reference_frames_directory",
        type=str,
        help="path containing the images to motion correct",
        required=True
    )
    parser.add_argument(
        "-sfd",
        "--sequence_frames_directory",
        type=str,
        help="reference frame directory",
        required=True
    )
    parser.add_argument(
        "-gi",
        "--gate_index",
        type=int,
        default=1,
        help="index of the reference frame [index starts from 1]",
    )
    parser.add_argument(
        "-r",
        "--registration",
        type=str,
        choices=["rigid", "affine", "deformable"],
        default='deformable',
        help="Type of registration: rigid | affine | deformable"
    )
    parser.add_argument(
        "-i",
        "--multi_resolution_iterations",
        type=str,
        default='100x50x25x0',
        help="Number of iterations for each resolution level"
    )

    args = parser.parse_args()

    # Paths
    reference_frames_directory = os.path.abspath(args.reference_frames_directory)
    sequence_frames_directory = os.path.abspath(args.sequence_frames_directory)

    # Other parameters
    registration = args.registration
    multi_resolution_iterations = args.multi_resolution_iterations
    gate_index = args.gate_index

    # Display logo and citation
    fileOp.display_logo_FALCON_cardiac()
    fileOp.display_citation()

    # Determine reference frame
    reference_frames = fileOp.get_files(reference_frames_directory, "*")

    # If the reference frames directory is empty:
    if len(reference_frames) < 1:
        print(f' The provided reference frames directory does not contain frames. '
              f'FALCON-cardiac will exit now.')
        exit()

    # Get needed data from sequence directory
    files_for_moco = fileOp.get_files(sequence_frames_directory, "*")
    last_filename = os.path.basename(files_for_moco[-1])
    current_file_extension = last_filename[last_filename.find('.'):]

    # If the reference frames directory contains a single file:
    if len(reference_frames) == 1:
        print(f' The provided reference frames directory contains only one frame. '
              f'This will be the sequence reference frame: {reference_frames[0]}')

        mean_reference_frame = os.path.join(sequence_frames_directory,
                                            f'vol{(len(files_for_moco) + 1):03}'
                                            f'_artificial_reference_frame{current_file_extension}')
        fileOp.copy_file(reference_frames[0], mean_reference_frame)
        print(f' The new reference frame will be: {mean_reference_frame}')

    # If the reference frames directory contains a multiple files:
    if len(reference_frames) > 1:
        print(f' The provided reference frames directory contains multiple ({len(reference_frames)}) frames. '
              f'The sequence reference frame will be created from them.')

        if gate_index > len(reference_frames):
            reference_frame_index = len(reference_frames) - 1
            print(f' ATTENTION - The provided gate index surpasses the number of existing reference frames.')
        elif gate_index < 0:
            reference_frame_index = 0
            print(f' ATTENTION - The provided gate index is smaller than 0.')
        else:
            reference_frame_index = gate_index - 1

        selected_reference_frame = reference_frames[reference_frame_index]
        print(f' Reference frame is {selected_reference_frame}')

        prepared_reference_frame_folder_path = os.path.join(reference_frames_directory, "reference_frame")
        if not os.path.exists(prepared_reference_frame_folder_path):
            os.mkdir(prepared_reference_frame_folder_path)

        # Move files in ascending order
        frame_index = 0
        for reference_frame in reference_frames:
            old_filename = os.path.basename(reference_frame)
            file_extension = old_filename[old_filename.find('.'):]

            if reference_frame == selected_reference_frame:
                new_filename = os.path.join(prepared_reference_frame_folder_path,
                                            f'vol{len(reference_frames) - 1:03}{file_extension}')
            else:
                new_filename = os.path.join(prepared_reference_frame_folder_path,
                                            f'vol{frame_index:03}{file_extension}')
                frame_index += 1

            fileOp.copy_file(reference_frame, new_filename)

        # run FALCON on reference frame folder
        spinner = Halo(text=f"Running FALCON on {prepared_reference_frame_folder_path}", spinner='dots')
        spinner.start()
        FALCON_reference = f"falcon " \
                           f"-m {prepared_reference_frame_folder_path} " \
                           f"-rf -1 " \
                           f"-sf 0 " \
                           f"-r {registration} " \
                           f"-i {multi_resolution_iterations}"
        subprocess.run(FALCON_reference, shell=True, capture_output=True)
        spinner.succeed(text=f"FALCON successfully performed motion correction on reference frames.")

        # sum reference frame and move to sequence folder
        mean_reference_frame = os.path.join(sequence_frames_directory,
                                            f'vol{(len(files_for_moco) + 1):03}'
                                            f'_artificial_reference_frame{current_file_extension}')
        corrected_reference_frames = fileOp.get_files(os.path.join(prepared_reference_frame_folder_path, "moco"),
                                                      constants.MOCO_FILE_PATTERN)
        print(f' Creating summed reference frame from following files:')
        for corrected_reference_frame in corrected_reference_frames:
            print(f"  + {corrected_reference_frame}")
        imageOp.create_mean_image_from_list(corrected_reference_frames, mean_reference_frame)
        print(f' The new reference frame will be: {mean_reference_frame}')

    # run FALCON on sequence folder
    spinner = Halo(text=f"Running FALCON on {sequence_frames_directory}", spinner='dots')
    spinner.start()
    FALCON_sequence = f"falcon " \
                      f"-m {sequence_frames_directory} " \
                      f"-rf -1 " \
                      f"-sf 0 " \
                      f"-r {registration} " \
                      f"-i {multi_resolution_iterations}"
    subprocess.run(FALCON_sequence, shell=True, capture_output=True)
    spinner.succeed(text=f"FALCON successfully performed motion correction on sequence frames.")

    corrected_frames = fileOp.get_files(os.path.join(sequence_frames_directory, "moco"), constants.MOCO_FILE_PATTERN)
    corrected_sequence_frames = corrected_frames[:-1]

    print(f' Creating summed reference frame from following files:')
    for corrected_sequence_frame in corrected_sequence_frames:
        print(f"  + {corrected_sequence_frame}")

    mean_frame = os.path.join(sequence_frames_directory, f"average_corrected_image{current_file_extension}")
    imageOp.create_mean_image_from_list(corrected_sequence_frames, mean_frame)
