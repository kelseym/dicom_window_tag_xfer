
# RE-TAG DICOM WINDOW CENTER & WIDTH

Given a reference dicom directory (DICOM), and a modified dicom directory (REFACED_DICOM,
copy Window Center & Width tags from reference dicom to a copy of the modified dicom.
Generate the modified dicom with the copied tags into a third directory (REFACED_DICOM_WCWW).
If Window Center & Width tags are not present in modified dicom, no-op

## Scan Level Utility (Container Service Command/Script)
scan_window_tags.py is a command line utility that takes the following arguments:
- `--reference` (required): reference dicom directory
- `--modified` (required): modified dicom directory
- `--output` (required): output directory for the modified dicom with copied Window Center & Width tags

This utility is intended to be used in the context of the XNAT Container Service at the scan level:
- `registry.nrg.wustl.edu/docker/nrg-repo/dicom_window_tag_xfer`

## Site Level Script (Archive Access Container/Script)
wcww_retag_all.py is a python script that takes the following arguments:
- `-u` (required): XNAT username
- `-p` (required/prompt): XNAT password
- `-s` (required): XNAT server
- `--project` (required): XNAT project
- `--root` (default=/input): root directory for processing. Must include at least `EXPERIMENT/scans/SCAN`
- `--reference` (default=DICOM): reference dicom directory label
- `--modified` (default=REFACED_DICOM): modified dicom directory label
- `--output` (default=REFACED_DICOM_WCWW): output dicom directory label
- `-v` (default=False): verbose output

### Example execution via Docker
Note that:
- `docker run -ti --rm -v $PWD:/input/WUSTL_002_20120421182223  registry.nrg.wustl.edu/docker/nrg-repo/dicom_window_tag_xfer:0.3 python3 wcww_retag_all.py --url http://snipr-shadow01.nrg.wustl.edu:8080 -u username --project WashU`
- Note that a session directory is mapped in such a way that the script can read directory name 'WUSTL_002_20120421182223'.
- The default --root is /input, so the script will look for the DICOM, REFACED_DICOM, and REFACED_DICOM_WCWW directories under /input/WUSTL_002_20120421182223
- User will be prompted for password if not supplied