#!/bin/bash
# Run image tests on compute node
# Usage: ./run_image_tests.bash [--date YYYYMMDD] [--auto]

set -e

DATE_STAMP="${DATE_STAMP:-$(date +%Y%m%d)}"
AUTO_ALLOCATE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --date)
            DATE_STAMP="$2"
            shift 2
            ;;
        --auto)
            AUTO_ALLOCATE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--date YYYYMMDD] [--auto]"
            exit 1
            ;;
    esac
done

ZPPY_ENV="test-zppy-main-${DATE_STAMP}-env"
ZPPY_DIR="$HOME/ez/zppy"
CONDA_PROFILE="$HOME/miniforge3/etc/profile.d/conda.sh"

if [ "$AUTO_ALLOCATE" = true ]; then
    echo "Auto-allocating compute node and running tests..."
    salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm << EOFALLOC
source ~/.bashrc
lcrc_conda # Run conda activation function defined in ~/.bashrc
conda activate $ZPPY_ENV
cd $ZPPY_DIR
pytest tests/integration/test_images.py
cat test_images_summary.md
EOFALLOC
else
    # DEFAULT
    # Assume we're already on a compute node or user will allocate manually
    echo "Running image tests..."
    echo "If not on compute node, first run:"
    echo "  salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm"
    echo ""

    source "$CONDA_PROFILE"
    conda activate "$ZPPY_ENV"
    cd "$ZPPY_DIR"
    pytest tests/integration/test_images.py
    cat test_images_summary.md
fi
