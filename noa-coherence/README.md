# Sentinel-1 InSAR Coherence Processing Pipeline

## Table of Contents

- [Introduction](#introduction)
- [What is Coherence?](#what-is-coherence)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Command-Line Arguments](#command-line-arguments)
  - [Example](#example)
- [Functionality](#functionality)
- [Contributing](#contributing)
- [License](#license)

## Introduction

The **Sentinel-1 InSAR Coherence Processing Pipeline** is a Python-based tool designed to process Sentinel-1 Single Look Complex (SLC) products using the [SNAP](http://step.esa.int/main/download/) (Sentinel Application Platform) framework via the SNAPPY python library. This pipeline facilitates the generation of coherence products, which are essential for various interferometric analyses, including surface deformation studies and terrain mapping.

## What is Coherence?

In the context of Interferometric Synthetic Aperture Radar (InSAR), **coherence** is a measure of the similarity between two SAR images taken from slightly different positions or at different times. It quantifies the degree of correlation between the phase and amplitude of the backscattered radar signals from two Synthetic Aperture Radar (SAR) images. High coherence values indicate stable scattering surfaces with minimal changes between acquisitions, while low coherence suggests significant changes or noise.

Coherence is crucial for:

- **Interferogram Quality:** High coherence ensures reliable phase information for interferometric measurements.
- **Surface Deformation Analysis:** Identifying areas with consistent scattering for accurate displacement measurements.
- **Terrain Mapping:** Enhancing the precision of digital elevation models (DEMs).

## Prerequisites

Before running the InSAR Coherence Processing Pipeline, ensure that the following software and dependencies are installed:

- **Python 3.9 or higher**
- **SNAP (Sentinel Application Platform) 8.x or higher**
- **Java Runtime Environment (JRE) 8 or higher**
- **Required Python Libraries:**
  - `jpy`
  - `snappy`
  - `argparse`
  - `sys`

### Installing SNAP

Download and install SNAP from the [official ESA website](http://step.esa.int/main/download/). Follow the installation instructions specific to your operating system.

### Setting Up Python Environment

It's recommended to use a virtual environment to manage dependencies:

```bash
# Create a virtual environment
python3 -m venv insar_env

# Activate the virtual environment
# On Windows:
insar_env\Scripts\activate
# On macOS/Linux:
source insar_env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install required Python libraries
pip install jpy snappy argparse
```

> **Note:** The `snappy` library requires SNAP to be correctly installed and configured. Ensure that the `SNAP_HOME` environment variable points to your SNAP installation directory.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/sentinel1-insar-pipeline.git
   cd sentinel1-insar-pipeline
   ```

2. **Install Dependencies:**

   Ensure that all prerequisites are met as outlined above.

3. **Configure SNAP:**

   Make sure that SNAP is properly installed and that the `snappy` module is correctly configured. You may need to run the following command to set up `snappy`:

   ```bash
   # Navigate to the snappy folder
   cd $SNAP_HOME/snappy

   # Install snappy
   python setup.py install
   ```

## Usage

The InSAR Coherence Processing Pipeline requires two Sentinel-1 SLC products (master and slave) to generate coherence products. The script accepts several command-line arguments to customize the processing parameters.

### Command-Line Arguments

```bash
usage: insar_pipeline.py [-h] master slave outpath minX minY maxX maxY
```

**Positional Arguments:**

1. **master** (`str`):  
   Path to the master Sentinel-1 SLC product file.

2. **slave** (`str`):  
   Path to the slave Sentinel-1 SLC product file.

3. **outpath** (`str`):  
   Directory path where the output products will be saved.

4. **minX** (`float`):  
   Minimum longitude of the bounding box (in decimal degrees).

5. **minY** (`float`):  
   Minimum latitude of the bounding box (in decimal degrees).

6. **maxX** (`float`):  
   Maximum longitude of the bounding box (in decimal degrees).

7. **maxY** (`float`):  
   Maximum latitude of the bounding box (in decimal degrees).

### Example

```bash
python insar_pipeline.py \
  /path/to/master_SLC.dim \
  /path/to/slave_SLC.dim \
  /path/to/output_directory \
  -123.45 37.77 -122.45 38.77 \
```

**Explanation:**

- **master_SLC.dim**: Path to the master Sentinel-1 SLC product.
- **slave_SLC.dim**: Path to the slave Sentinel-1 SLC product.
- **EVT12345**: Event identifier.
- **/path/to/output_directory**: Directory where outputs will be saved.
- **-123.45 37.77 -122.45 38.77**: Bounding box coordinates (minX, minY, maxX, maxY).
- **additional_parameter_value**: Placeholder for any additional parameter required by the pipeline.

## Functionality

The pipeline consists of several functions that handle different processing steps. Below is an overview of the key functions:

### 1. `read(filename: str) -> Product`

Reads a Sentinel-1 product from the specified filename.

### 2. `write(product, filename: str)`

Writes a product to a file in GeoTIFF format.

### 3. `topsar_split(product, swath: str, pol: str) -> Product`

Splits a TOPSAR product into subswaths and polarizations.

### 4. `topsar_merge(product, pol: str) -> Product`

Merges split TOPSAR products based on polarization.

### 5. `apply_orbit_file(product, mode: int) -> Product`

Applies orbit file corrections to the product.  
**Parameters:**
- `mode`: `1` for Restituted orbit, else Precise orbit.

### 6. `back_geocoding(product) -> Product`

Performs back-geocoding on the product using a Digital Elevation Model (DEM).

### 7. `topsar_deburst(product, pol: str) -> Product`

Removes burst overlaps from TOPSAR products based on polarization.

### 8. `topophase_removal(product) -> Product`

Removes topographic phase from the interferogram.

### 9. `coherence_generation(product) -> Product`

Generates coherence from the product.

### 10. `geometric_correction(product, polarisation: str, to_print: bool = True) -> Product`

Performs geometric correction on the product.

### 11. `subset(product, bbox: list, to_print: bool = True) -> Optional[Product]`

Subsets the product using a bounding box.

### 12. `insar_pipeline(master: str, slave: str, outpath: str, event_id: str, bbox: list, other_param)`

Main InSAR processing pipeline that orchestrates the entire workflow using the above functions.

## Contributing

Contributions are welcome! Please follow these steps to contribute:

1. **Fork the Repository**

2. **Create a New Branch**

   ```bash
   git checkout -b feature/YourFeatureName
   ```

3. **Commit Your Changes**

   Follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification for commit messages.

4. **Push to the Branch**

   ```bash
   git push origin feature/YourFeatureName
   ```

5. **Open a Pull Request**

   Provide a clear description of your changes and reference any related issues.

## License

This project is licensed under the [MIT License](LICENSE).

---

**Note:** Ensure that all paths and parameters are correctly specified when running the script. For any issues or feature requests, please open an [issue](https://github.com/yourusername/sentinel1-insar-pipeline/issues) on GitHub.

---

### Additional Tips:

- **Verify Markdown Rendering:** After pasting the content into your `README.md`, preview it on GitHub or your preferred Markdown viewer to ensure that all sections, links, and code blocks render correctly.
- **Update Repository Links:** Replace `https://github.com/yourusername/sentinel1-insar-pipeline.git` and other placeholder links with your actual repository URLs.
- **Customize as Needed:** Feel free to modify the content to better fit your project's specifics, such as adding more detailed usage examples, screenshots, or additional sections relevant to your users.

By following these steps, your `README.md` should display properly and provide comprehensive information to users and contributors of your project.
