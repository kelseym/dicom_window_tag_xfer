import argparse
from pydicom import dcmread
from pydicom.misc import is_dicom
import os


def scan_window_tags():
    parser = argparse.ArgumentParser(description="Reads Window Center & Width DICOM tags from a file in --reference."
                                                 "Window tags are applied to all DICOM files in --modified."
                                                 "Output is written to --output."
                                                 "Window Center & Width Ecplanation also is copied, if present.")
    parser.add_argument('--reference', required=True, help='Reference DICOM file/folder. e.g. DICOM')
    parser.add_argument('--modified', required=True, help='Modified DICOM folder. e.g. REFACED_DICOM')
    parser.add_argument('--output', required=True, help='Output folder. e.g. REFACED_DICOM_WCWW')
    args = parser.parse_args()

    # Get Window Center, Window Width, and Explanation tags from modified
    [center, width, explanation] = get_window_tags(args.modified)
    if center is not None and width is not None:
        print("Modified DICOM files already contain Window Center and Window Width tags.")
        exit(0)

    # Get Window Center, Window Width, and Explanation tags from reference
    [center, width, explanation] = get_window_tags(args.reference)

    if center is None or width is None:
        print("Reference file does not contain Window Center and Window Width tags.")
        exit(0)
    else:
        print(f"Window Center: {center}, Window Width: {width}")
        if explanation:
            print(f"Window Explanation: {explanation}")

    # Create new dicom files with widows tags from reference
    for root, dirs, files in os.walk(args.modified):
        for file in files:
            dicom_file = os.path.join(root, file)
            if not is_dicom(str(dicom_file)):
                continue
            dicom = dcmread(dicom_file)
            dicom.WindowCenter = center
            dicom.WindowWidth = width
            if explanation:
                dicom.WindowCenterWidthExplanation = explanation
            dicom.save_as(str(os.path.join(args.output, file)))

    # Excluding *.xml files (XNAT catalog files), check that files from the 'modified' directory were copied
    for root, dirs, files in os.walk(args.modified):
        err = False
        for file in files:
            if file.endswith(".xml"):
                continue
            if not os.path.exists(os.path.join(args.output, file)):
                print(f"Error: {file} was not copied.")
                err = True
        if err:
            exit(1)


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
    scan_window_tags()
