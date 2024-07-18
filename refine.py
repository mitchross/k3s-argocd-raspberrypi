import os
import yaml
from pathlib import Path

def refine_folder_structure(root):
    manifests_dir = root / 'manifests'
    for category in ['infrastructure', 'operators', 'applications']:
        category_dir = manifests_dir / category
        for app_dir in category_dir.iterdir():
            if app_dir.is_dir():
                refine_application_folder(app_dir)

def refine_application_folder(app_dir):
    yaml_files = list(app_dir.glob('*.yaml'))
    
    # Rename main YAML file if it's not a Helm chart
    if len(yaml_files) == 1 and yaml_files[0].name != 'values.yaml':
        yaml_files[0].rename(app_dir / 'main.yaml')
    
    # Combine multiple YAML files (excluding values.yaml) into a single file
    non_values_yaml = [f for f in yaml_files if f.name != 'values.yaml']
    if len(non_values_yaml) > 1:
        combine_yaml_files(app_dir, non_values_yaml)
    
    # Create a kustomization.yaml file
    create_kustomization_file(app_dir)

def combine_yaml_files(app_dir, yaml_files):
    combined_docs = []
    for file in yaml_files:
        with open(file, 'r') as f:
            docs = list(yaml.safe_load_all(f))
            combined_docs.extend(docs)
        file.unlink()  # Remove the original file
    
    with open(app_dir / 'main.yaml', 'w') as f:
        yaml.safe_dump_all(combined_docs, f)

def create_kustomization_file(app_dir):
    resources = [f.name for f in app_dir.glob('*.yaml') if f.name != 'values.yaml']
    kustomization = {
        'apiVersion': 'kustomize.config.k8s.io/v1beta1',
        'kind': 'Kustomization',
        'resources': resources
    }
    with open(app_dir / 'kustomization.yaml', 'w') as f:
        yaml.safe_dump(kustomization, f)

def main():
    root = Path.cwd()
    refine_folder_structure(root)
    print("Folder structure refinement completed. Please review the changes.")

if __name__ == "__main__":
    main()