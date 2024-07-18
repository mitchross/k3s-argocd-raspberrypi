#!/bin/bash

# Set the root directory of your project
PROJECT_ROOT="$(pwd)"

# Create new directory structure
mkdir -p "$PROJECT_ROOT/argocd/applicationsets"
mkdir -p "$PROJECT_ROOT/manifests/infrastructure"
mkdir -p "$PROJECT_ROOT/manifests/operators"
mkdir -p "$PROJECT_ROOT/manifests/applications"

# Function to categorize files
categorize_file() {
    local file="$1"
    local filename=$(basename "$file")
    
    case "$filename" in
        kube-system.yaml|longhorn-system.yaml|crossplane-system.yaml)
            echo "infrastructure"
            ;;
        cert-manager.yaml|external-secrets.yaml|external-dns.yaml|reloader.yaml|rabbitmq-operator.yaml|postgres-operator.yaml)
            echo "operators"
            ;;
        *)
            echo "applications"
            ;;
    esac
}

# Move existing yaml files to their new locations
for file in "$PROJECT_ROOT"/*.yaml; do
    if [ -f "$file" ]; then
        category=$(categorize_file "$file")
        mv "$file" "$PROJECT_ROOT/manifests/$category/"
    fi
done

# Create new ApplicationSet for project structure
cat << EOF > "$PROJECT_ROOT/argocd/applicationsets/project-structure.yaml"
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: project-structure
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - name: infrastructure
          - name: operators
          - name: applications
  template:
    metadata:
      name: '{{.name}}'
    spec:
      project: homelab
      source:
        repoURL: https://github.com/mitchross/k8s-homelab-argocd.git
        targetRevision: HEAD
        path: manifests/{{.name}}
      destination:
        server: https://kubernetes.default.svc
        namespace: argocd
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
EOF

# Extract and modify the existing ApplicationSet
sed -n '/^apiVersion: argoproj.io\/v1alpha1/,/^---/p' "$PROJECT_ROOT/manifests/applications/argocd.yaml" | \
sed 's/path: manifest\/\*\.yaml/path: manifests\/**\/*.yaml/' > "$PROJECT_ROOT/argocd/applicationsets/homelab-manifest.yaml"

# Update the repoURL in the new ApplicationSet if necessary
sed -i 's|https://github\.com/mitchross/k8s-homelab-argocd\.git|YOUR_REPO_URL|g' "$PROJECT_ROOT/argocd/applicationsets/homelab-manifest.yaml"

echo "Migration completed. Please review the changes and update any remaining references manually."
echo "Don't forget to update the repoURL in argocd/applicationsets/homelab-manifest.yaml if necessary."