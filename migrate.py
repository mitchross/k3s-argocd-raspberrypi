import os
import shutil
import yaml
from pathlib import Path

def create_directory_structure(root):
    directories = [
        'argocd/applicationsets',
        'argocd/applications',
        'manifests/infrastructure',
        'manifests/operators',
        'manifests/applications'
    ]
    for directory in directories:
        Path(root / directory).mkdir(parents=True, exist_ok=True)

def categorize_file(filename):
    infrastructure = ['kube-system', 'longhorn-system', 'crossplane-system']
    operators = ['cert-manager', 'external-secrets', 'external-dns', 'reloader', 'rabbitmq-operator', 'postgres-operator']
    
    if isinstance(filename, Path):
        name = filename.stem
    else:
        name = filename

    if name in infrastructure:
        return 'infrastructure'
    elif name in operators:
        return 'operators'
    else:
        return 'applications'

def handle_helm_application(app, root):
    app_name = app['metadata'].get('name', 'unnamed')
    category = categorize_file(app_name)
    
    # Create a folder for the application
    app_folder = root / 'manifests' / category / app_name
    app_folder.mkdir(parents=True, exist_ok=True)

    # Create a values.yaml file for the Helm chart
    values_file = app_folder / "values.yaml"
    with open(values_file, 'w') as f:
        yaml.dump(app['spec']['source'].get('helm', {}).get('valuesObject', {}), f)

    # Update the Application to point to the new values file
    app['spec']['source']['helm'] = {
        'valueFiles': [f"../../manifests/{category}/{app_name}/values.yaml"]
    }

    # Save the updated Application
    app_file = root / 'argocd' / 'applications' / f"{app_name}-application.yaml"
    with open(app_file, 'w') as f:
        yaml.dump(app, f)

def process_yaml_file(file_path, root):
    with open(file_path, 'r') as file:
        documents = list(yaml.safe_load_all(file))

    application_sets = []
    argocd_applications = []
    other_resources = []

    for doc in documents:
        if doc and doc.get('kind') == 'ApplicationSet':
            application_sets.append(doc)
        elif doc and doc.get('kind') == 'Application':
            argocd_applications.append(doc)
        elif doc:
            other_resources.append(doc)

    # Save ApplicationSets
    for app_set in application_sets:
        app_set_name = app_set['metadata'].get('name', 'unnamed')
        app_set_path = root / 'argocd' / 'applicationsets' / f"{app_set_name}-applicationset.yaml"
        with open(app_set_path, 'w') as f:
            yaml.dump(app_set, f)

    # Handle ArgoCD Applications
    for app in argocd_applications:
        if 'helm' in app.get('spec', {}).get('source', {}):
            handle_helm_application(app, root)
        else:
            app_name = app['metadata'].get('name', 'unnamed')
            argocd_app_path = root / 'argocd' / 'applications' / f"{app_name}-application.yaml"
            with open(argocd_app_path, 'w') as f:
                yaml.dump(app, f)

    # Save other resources
    if other_resources:
        category = categorize_file(file_path)
        app_name = file_path.stem
        app_folder = root / 'manifests' / category / app_name
        app_folder.mkdir(parents=True, exist_ok=True)
        new_path = app_folder / file_path.name
        with open(new_path, 'w') as f:
            yaml.dump_all(other_resources, f)

def create_project_structure_applicationset(root):
    content = {
        'apiVersion': 'argoproj.io/v1alpha1',
        'kind': 'ApplicationSet',
        'metadata': {
            'name': 'project-structure',
            'namespace': 'argocd'
        },
        'spec': {
            'generators': [{
                'list': {
                    'elements': [
                        {'name': 'infrastructure'},
                        {'name': 'operators'},
                        {'name': 'applications'}
                    ]
                }
            }],
            'template': {
                'metadata': {'name': '{{.name}}'},
                'spec': {
                    'project': 'homelab',
                    'source': {
                        'repoURL': 'https://github.com/mitchross/k8s-homelab-argocd.git',
                        'targetRevision': 'HEAD',
                        'path': 'manifests/{{.name}}'
                    },
                    'destination': {
                        'server': 'https://kubernetes.default.svc',
                        'namespace': 'argocd'
                    },
                    'syncPolicy': {
                        'automated': {
                            'prune': True,
                            'selfHeal': True
                        }
                    }
                }
            }
        }
    }
    
    file_path = root / 'argocd' / 'applicationsets' / 'project-structure.yaml'
    with open(file_path, 'w') as f:
        yaml.dump(content, f)

def update_homelab_manifest_applicationset(root):
    file_path = root / 'argocd' / 'applicationsets' / 'homelab-manifest-applicationset.yaml'
    if file_path.exists():
        with open(file_path, 'r') as f:
            content = yaml.safe_load(f)
        
        # Update the path in the ApplicationSet
        if 'spec' in content and 'generators' in content['spec']:
            for generator in content['spec']['generators']:
                if 'git' in generator:
                    generator['git']['files'] = [{'path': 'manifests/**/*.yaml'}]
        
        with open(file_path, 'w') as f:
            yaml.dump(content, f)

def remove_old_structure(root):
    old_manifest_dir = root / 'manifest'
    if old_manifest_dir.exists():
        shutil.rmtree(old_manifest_dir)

def main():
    root = Path.cwd()
    create_directory_structure(root)

    # Process files in manifest directory
    manifest_dir = root / 'manifest'
    if manifest_dir.exists():
        for file in manifest_dir.glob('*.yaml'):
            process_yaml_file(file, root)

        # Process files in manifest/apps directory and its subdirectories
        apps_dir = manifest_dir / 'apps'
        if apps_dir.exists():
            for file in apps_dir.rglob('*.yaml'):
                if file.is_file():
                    process_yaml_file(file, root)

    create_project_structure_applicationset(root)
    update_homelab_manifest_applicationset(root)

    # Remove old directory structure
    remove_old_structure(root)

    print("Migration completed. Please review the changes and update any remaining references manually.")
    print("Don't forget to update the repoURL in argocd/applicationsets/ files if necessary.")

if __name__ == "__main__":
    main()