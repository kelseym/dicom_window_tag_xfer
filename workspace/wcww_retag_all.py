#~ Given an XNAT directory tree, search for REFACED_DICOM resources (with files)
#~ and create REFACED_DICOM_WCWW resources with Window Center and Window Width tags
# from the corresponding DICOM files.

import argparse
from pydicom import dcmread
from pydicom.misc import is_dicom
import os
import logging
import getpass
import xnat
import time


def wcww_retag_all():
    parser = argparse.ArgumentParser(description="Given an XNAT directory tree, search for REFACED_DICOM resources "
                                                 "(with files) and create REFACED_DICOM_WCWW resources with "
                                                 "Window Center and Window Width tags from the corresponding "
                                                 "DICOM files."
                                                 "XNAT connection is used to create new resources and refresh the catalog."
                                     )
    parser.add_argument('-u', '--user', required=True, help='Target XNAT username')
    parser.add_argument('-p', '--password', required=False, help='XNAT password')
    parser.add_argument('--url', required=True, help='Target XNAT base URL')
    parser.add_argument('--project', required=True, help='Target XNAT project ID')
    parser.add_argument('--root', required=False, default='/input',
                        help='XNAT directory tree. '
                             'Archive directory must include at least EXPERIMENT/scans/SCAN'
                             'e.g. /data/xnat/archive/PROJECT_ID')
    parser.add_argument('--reference', required=False, default='DICOM',
                        help='Reference DICOM resource pattern. e.g. DICOM')
    parser.add_argument('--modified', required=False, default='REFACED_DICOM',
                        help='Modified DICOM pattern. e.g. REFACED_DICOM')
    parser.add_argument('--output', required=False, default='REFACED_DICOM_WCWW',
                        help='Output resource. e.g. REFACED_DICOM_WCWW')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.password:
        args.password = getpass.getpass(prompt='Enter XNAT password: ')

    # Find all scan directories that contain a populated 'modified' folder and a 'reference' folder
    # Exclude directories that already contain a populated 'output' folder
    refaced_dicom_resource_scans = find_resources(args.root, args.reference, args.modified, args.output)

    create_retagged_resources(refaced_dicom_resource_scans, args)


def find_resources(root, reference, modified, output):
    resource_scans = []
    for root, dirs, files in os.walk(root):
        if modified in dirs and reference in dirs:
            # Check for existing and populated output directory
            if output in dirs:
                output_dir = str(os.path.join(root, output))
                if list_directory(output_dir, exclude=".xml"):
                    logging.debug(f"Skipping: {output_dir}. Already contains files.")
                    continue
            # Check for valid and populated directories
            dicom_exists = False
            modified_dir = str(os.path.join(root, modified))
            for file in os.listdir(modified_dir):
                if os.path.isfile(str(os.path.join(modified_dir, file))) and is_dicom(os.path.join(modified_dir, file)):
                    dicom_exists = True
                    break
            if not dicom_exists:
                logging.debug(f"Skipping: {modified_dir}. Does not contain any DICOM files.")
                continue
            resource_scans.append(os.path.join(root))
    return resource_scans


# For each scan directory, 1) check for DICOM files in the 'modified' folder
#                          2) check for DICOM files in the 'reference' folder
#                          3) create a 'output' files with Window Center and Window Width tags
#                             from the corresponding DICOM files
def create_retagged_resources(refaced_dicom_resource_scans, args):
    with xnat.connect(args.url, user=args.user, password=args.password) as connection:
        project = args.project
        modified = args.modified
        reference = args.reference
        output = args.output
        for scan_dir in refaced_dicom_resource_scans:
            try:
                xnat_resource = register_new_retagged_resources(connection, project, scan_dir, output)
                if xnat_resource:
                    populate_new_retagged_resources(scan_dir, modified, reference, output)
                    refresh_resource_catalog(connection, xnat_resource)
            except Exception as e:
                logging.error(f"Error creating retagged resources for {scan_dir}\n{e}")

def refresh_resource_catalog(connection, xnat_resource):
    try:
        scan = xnat_resource.parent
        experiment = scan.parent
        subject = experiment.parent
        project = subject.parent
        if experiment and scan and subject and project:
            target = f'/archive/experiments/{experiment.id}/scans/{scan.id}/resources/{xnat_resource.label}'
            connection.post(f'/data/services/refresh/catalog/?resource={target}')
            # Just chill out for a few seconds so we don't overwhelm the server
            time.sleep(5)

    except Exception as e:
        logging.error(f"Error refreshing resource catalog:{xnat_resource}\n{e}")


def register_new_retagged_resources(connection, project, scan_dir, resource_label):
    # Parse the scan directory and register the new resource with the XNAT server.
    # /WUSTL_002_04242012/SCANS/2'
    if not scan_dir or len(scan_dir.split('/')) < 3:
        raise ValueError(f"Error: Scan directory must include an experiment label at position -3: {scan_dir}")
    scan = scan_dir.split('/')[-1]
    experiment = scan_dir.split('/')[-3]
    xnat_project = connection.projects[project]
    if not xnat_project:
        raise ValueError(f"Project with ID '{project}' not found.")
    xnat_experiment = xnat_project.experiments[experiment]
    if not experiment:
        raise ValueError(f"Experiment with label '{experiment}' not found.")
    xnat_scan = xnat_experiment.scans[scan]
    if not scan:
        raise ValueError(f"Scan with ID '{scan}' not found.")
    # Create a new resource
    new_resource = xnat_scan.resources.get(resource_label)
    if not new_resource:
        return connection.classes.ResourceCatalog(parent=xnat_scan, label=resource_label)
    return new_resource


def populate_new_retagged_resources(scan_dir, modified, reference, output):
    modified_dir = str(os.path.join(scan_dir, modified))
    reference_dir = str(os.path.join(scan_dir, reference))
    output_dir = str(os.path.join(scan_dir, output))

    # Check for valid and populated directories
    if not os.path.exists(modified_dir) or not os.path.exists(reference_dir):
        logging.error(f"Error: {modified_dir} or {reference_dir} does not exist.")
        return
    dicom_exists = False
    for file in os.listdir(modified_dir):
        if os.path.isfile(os.path.join(modified_dir, file)) and is_dicom(os.path.join(modified_dir, file)):
            dicom_exists = True
            break
    if not dicom_exists:
        logging.error(f"Error: {modified_dir} does not contain any DICOM files.")
        return
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        if list_directory(output_dir, exclude=".xml"):
            logging.error(f"Error: {output_dir} is not empty.")
            return

    # Get Window Center, Window Width, and Explanation tags from modified
    [mod_center, mod_width, mod_explanation] = get_window_tags(modified_dir)
    if mod_center is not None and mod_width is not None:
        logging.error(f"Modified DICOM files already contain Window Center and Window Width tags in {modified_dir}")
        return

    # Get Window Center, Window Width, and Explanation tags from reference
    [ref_center, ref_width, ref_explanation] = get_window_tags(reference_dir)

    if ref_center is None or ref_width is None:
        logging.error(f"Reference file does not contain Window Center and Window Width tags in {reference_dir}")
        return
    else:
        logging.debug(f"Window Center: {ref_center}, Window Width: {ref_width} "
                      f"Window Explanation: {ref_explanation} in {reference_dir}")

    # Create new dicom files with widows tags from reference
    for root, dirs, files in os.walk(modified_dir):
        for file in files:
            dicom_file = os.path.join(root, file)
            if os.path.isdir(str(dicom_file)) or not is_dicom(str(dicom_file)):
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
                if os.path.isdir(str(dicom_file)) or not is_dicom(str(dicom_file)):
                    continue
                center, width, explanation = get_window_tags(dicom_file)
                if center is not None:
                    return center, width, explanation
    else:
        dicom = dcmread(dicom_file_or_dir)
        center = dicom.WindowCenter if 'WindowCenter' in dicom else None
        width = dicom.WindowWidth if 'WindowWidth' in dicom else None
        explanation = dicom.WindowCenterWidthExplanation if 'WindowCenterWidthExplanation' in dicom else None
        if center and width:
            return center, width, explanation if explanation else None
    return None, None, None


def list_directory(directory, exclude=None):
    files = []
    for file in os.listdir(directory):
        if exclude is not None and not exclude in file:
            files.append(file)
    return files


if __name__ == '__main__':
    wcww_retag_all()
