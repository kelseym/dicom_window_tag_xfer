#~ Given an XNAT directory tree, search for REFACED_DICOM resources (with files)
#~ and create REFACED_DICOM_WCWW resources with Window Center and Window Width tags
# from the corresponding DICOM files.

import argparse
from pydicom import dcmread
from pydicom.misc import is_dicom
import os
import logging

def wcww_retag_all():
    parser = argparse.ArgumentParser(description="Given an XNAT directory tree, search for REFACED_DICOM resources "
                                                 "(with files) and create REFACED_DICOM_WCWW resources with "
                                                 "Window Center and Window Width tags from the corresponding "
                                                 "DICOM files.")
    parser.add_argument('--root', required=True, help='XNAT directory tree. e.g. /data/xnat/archive/PROJECT_ID')
    parser.add_argument('--reference', required=False, default='DICOM',
                        help='Reference DICOM resource pattern. e.g. DICOM')
    parser.add_argument('--modified', required=False, default='REFACED_DICOM',
                        help='Modified DICOM pattern. e.g. REFACED_DICOM')
    parser.add_argument('--output', required=False, default='REFACED_DICOM_WCWW',
                        help='Output resource. e.g. REFACED_DICOM_WCWW')
    args = parser.parse_args()

    # Find all scan directories that contain a populated 'modified' folder and a 'reference' folder
    refaced_dicom_resources = find_resources(args.root, args.reference, args.modified)

    create_retagged_resources(refaced_dicom_resources, args.modified, args.reference, args.output)


def find_resources(root, reference, modified):
    resources = []
    for root, dirs, files in os.walk(root):
        if modified in dirs and reference in dirs:
            resources.append(os.path.join(root))
    return resources

# For each scan directory, 1) check for DICOM files in the 'modified' folder
#                          2) check for DICOM files in the 'reference' folder
#                          3) create a 'output' files with Window Center and Window Width tags
#                             from the corresponding DICOM files
def create_retagged_resources(refaced_dicom_resources, modified, reference, output):
    for resource in refaced_dicom_resources:
        modified_dir = str(os.path.join(resource, modified))
        reference_dir = str(os.path.join(resource, reference))
        output_dir = str(os.path.join(resource, output))

        # Check for valid and populated directories
        if not os.path.exists(modified_dir) or not os.path.exists(reference_dir):
            logging.error(f"Error: {modified_dir} or {reference_dir} does not exist.")
            continue
        dicom_exists = False
        for file in os.listdir(modified_dir):
            if is_dicom(os.path.join(modified_dir, file)):
                dicom_exists = True
                break
        if not dicom_exists:
            logging.error(f"Error: {modified_dir} does not contain any DICOM files.")
            continue
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        else:
            if os.listdir(output_dir):
                logging.error(f"Error: {output_dir} is not empty.")
                continue

        # Get Window Center, Window Width, and Explanation tags from modified
        [mod_center, mod_width, mod_explanation] = get_window_tags(modified_dir)
        if mod_center is not None and mod_width is not None:
            logging.error(f"Modified DICOM files already contain Window Center and Window Width tags in {modified_dir}")
            continue

        # Get Window Center, Window Width, and Explanation tags from reference
        [ref_center, ref_width, ref_explanation] = get_window_tags(reference_dir)

        if ref_center is None or ref_width is None:
            logging.error(f"Reference file does not contain Window Center and Window Width tags in {reference_dir}")
            continue
        else:
            logging.debug(f"Window Center: {ref_center}, Window Width: {ref_width} "
                          f"Window Explanation: {ref_explanation} in {reference_dir}")

        # Create new dicom files with widows tags from reference
        for root, dirs, files in os.walk(modified_dir):
            for file in files:
                dicom_file = os.path.join(root, file)
                if not is_dicom(str(dicom_file)):
                    continue
                dicom = dcmread(dicom_file)
                dicom.WindowCenter = ref_center
                dicom.WindowWidth = ref_width
                if ref_explanation:
                    dicom.WindowCenterWidthExplanation = ref_explanation
                dicom.save_as(str(os.path.join(output_dir, file)))

        # Excluding *.xml files (XNAT catalog files), check that files from the 'modified' directory were copied
        for root, dirs, files in os.walk(modified_dir):
            for file in files:
                if file.endswith(".xml"):
                    continue
                if not os.path.exists(os.path.join(output_dir, file)):
                    print(f"Error: {file} was not copied.")
            print(f"Files from {modified_dir} were retagged to {output_dir}")

# Return the Window Center, Window Width, and Explanation tags from a DICOM file (or first file in a directory)
def get_window_tags(dicom_file_or_dir):
    if os.path.isdir(dicom_file_or_dir):
        for root, dirs, files in os.walk(dicom_file_or_dir):
            for file in files:
                dicom_file = os.path.join(root, file)
                if not is_dicom(str(dicom_file)):
                    continue
                center, width, explanation = get_window_tags(dicom_file)
                if center is not None:
                    return center, width, explanation
    else:
        dicom = dcmread(dicom_file_or_dir)
        center = dicom.WindowCenter if 'WindowCenter' in dicom  else None
        width = dicom.WindowWidth if 'WindowWidth' in dicom  else None
        explanation = dicom.WindowCenterWidthExplanation if 'WindowCenterWidthExplanation' in dicom  else None
        if center and width:
            return center, width, explanation if explanation else None
    return None, None, None

if __name__ == '__main__':
    wcww_retag_all()


