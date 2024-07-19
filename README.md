# Getting started

## Create cluster

```shell
curl -sfL https://get.k3s.io | sh -s - \
  --flannel-backend=none \
  --disable-kube-proxy \
  --disable servicelb \
  --disable-network-policy \
  --disable traefik \
  --cluster-init

```

## fix kubeconfig
``` shell 
mkdir -p $HOME/.kube
sudo cp -i /etc/rancher/k3s/k3s.yaml $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
echo "export KUBECONFIG=$HOME/.kube/config" >> $HOME/.bashrc
source $HOME/.bashrc
```


Add Gateway API CRDs

```shell
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/experimental-install.yaml
```

Remove taint on control-plane nodes to allow scheduling of all deployments (optional)

```shell
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

Add Cilium

```shell
kubectl kustomize --enable-helm infra/core/cilium | kubectl apply -f -
```

Add Sealed Secrets

```shell
kubectl kustomize --enable-helm infra/controllers/sealed-secrets | kubectl apply -f -
```

Get CF API token and create secret

```shell
CF_API_TOKEN=<CF_API_TOKEN>
kubectl -n cert-manager create secret generic cloudflare-api-token --from-literal=api-token=${CF_API_TOKEN} --dry-run=client -oyaml > cluster-issuer-cf-api-secret.yaml 
kubectl -n gateway create secret generic cloudflare-api-token --from-literal=api-token=${CF_API_TOKEN} --dry-run=client -oyaml > gateway-cf-api-secret.yaml 
```

Seal secret for Cluster Issuer

```shell
kubeseal -o yaml < cluster-issuer-cf-api-secret.yaml > infra/controllers/cert-manager/cloudflare-api-token.yaml
```

Add Cert-manager

```shell
kubectl kustomize --enable-helm infra/controllers/cert-manager | kubectl apply -f -
```

Seal secret for Gateway

```shell
kubeseal -o yaml < gateway-cf-api-secret.yaml > infra/network/gateway/cloudflare-api-token.yaml
```

Gateway

```shell
kubectl kustomize --enable-helm infra/network/gateway | kubectl apply -f -
```

Cloudflare tunnel

```shell
cloudflared tunnel create <NAME>
```

```shell
TUNNEL_CREDENTIALS=<CREDENTIALS_FILE>
kubectl -n cloudflared create secret generic tunnel-credentials --from-literal=credentials.json=$(cat ${TUNNEL_CREDENTIALS}) --dry-run=client -oyaml > tunnel-secret.yaml 
```

Seal CF tunnel secret

```shell
kubeseal -o yaml < tunnel-secret.yaml > infra/network/cloudflared/tunnel-credentials.yaml
```

```shell
kubectl apply -k infra/network/cloudflared
```

Get Tunnel ID (not Connector ID) and add DNS CNAME record with `<id>.cfargotunnel.com`

Add Argo CD

```shell
kubectl kustomize --enable-helm infra/core/argocd | kubectl apply -f -
```

Get Argo CD admin secret

```shell
kubectl -n argocd get secret argocd-initial-admin-secret -ojson | jq -r ' .data.password | @base64d'
```

Apply app-of-apps

```shell
kubectl apply -k sets
```

## Intel Device Plugin

```shell
kubectl kustomize --enable-helm infra/controllers/node-feature-discovery | kubectl apply -f -
```

```shell
kubectl kustomize --enable-helm infra/controllers/intel-device-plugins | kubectl apply -f -
```

```shell
kubectl get node -o 'jsonpath={.items[*].status.allocatable}' | jq 
```

## Proxmox CCM

https://kubernetes.io/docs/tasks/administer-cluster/running-cloud-controller/

```shell
veh@k8s-ctrl-01:~$ sudo vim /var/lib/kubelet/config.yaml
veh@k8s-ctrl-01:/var/lib/kubelet$ cat kubeadm-flags.env  
veh@k8s-ctrl-01:~$ sudo systemctl restart kubelet
veh@k8s-ctrl-01:/var/lib/kubelet$ cat kubeadm-flags.env 
KUBELET_KUBEADM_ARGS="--container-runtime-endpoint=unix:///var/run/containerd/containerd.sock --pod-infra-container-image=registry.k8s.io/pause:3.9"
KUBELET_EXTRA_ARGS="--cloud-provider=external"


veh@k8s-ctrl-01:/etc/sysconfig$ cat kubelet 
KUBELET_EXTRA_ARGS=
veh@k8s-ctrl-01:/etc/sysconfig$ cat kubelet 
KUBELET_EXTRA_ARGS="--node-ip=192.168.1.100 --cloud-provider=external"

veh@k8s-ctrl-01:/etc/default$ cat kubelet
KUBELET_EXTRA_ARGS="--node-ip=192.168.1.100 --cloud-provider=external"


sudo systemctl daemon-reload
sudo systemctl restart kubelet.service
```

> The basic definitions:
> * kubernetes region is a Proxmox cluster clusters[].region
> * kubernetes zone is a hypervisor host machine name

```shell
kubectl label no k8s-ctrl-01 topology.kubernetes.io/region=homelab
kubectl label no k8s-ctrl-01 topology.kubernetes.io/zone=abel
```
```shell
kubectl label no k8s-ctrl-02 topology.kubernetes.io/region=homelab
kubectl label no k8s-ctrl-02 topology.kubernetes.io/zone=euclid
```

https://github.com/sergelogvinov/proxmox-cloud-controller-manager

https://github.com/sergelogvinov/proxmox-cloud-controller-manager/issues/63
https://github.com/sergelogvinov/proxmox-cloud-controller-manager/issues/111

Create role CCM
Create user and grant permissions

```shell
pveum role add CCM -privs "VM.Audit"
pveum user add kubernetes@pve
pveum aclmod / -user kubernetes@pve -role CCM
pveum user token add kubernetes@pve ccm -privsep 0
```

```yaml
# config.yaml
clusters:
  - url: https://cluster-api-1.exmple.com:8006/api2/json
    insecure: false
    token_id: "kubernetes@pve!ccm"
    token_secret: "secret"
    region: cluster-1
```

```shell
kubeseal -o yaml < pve-ccm-secret.yaml > infra/controllers/proxmox-ccm/proxmox-ccm-secret.yaml
```

Install Proxmox CCM

```shell
kubectl apply -k infra/controllers/proxmox-ccm
```

## Proxmox CSI

https://github.com/sergelogvinov/proxmox-csi-plugin
https://github.com/sergelogvinov/proxmox-csi-plugin/issues/157

```shell
pveum role add CSI -privs "VM.Audit VM.Config.Disk Datastore.Allocate Datastore.AllocateSpace Datastore.Audit"
pveum user add kubernetes-csi@pve
pveum aclmod / -user kubernetes-csi@pve -role CSI
pveum user token add kubernetes-csi@pve csi -privsep 0
```

```shell
# config.yaml
clusters:
  - url: https://cluster-api-1.exmple.com:8006/api2/json
    insecure: false
    token_id: "kubernetes-csi@pve!csi"
    token_secret: "secret"
    region: Region-1
  - url: https://cluster-api-2.exmple.com:8006/api2/json
    insecure: false
    token_id: "kubernetes-csi@pve!csi"
    token_secret: "secret"
    region: Region-2
```

```shell
kubectl -n csi-proxmox create secret generic proxmox-csi-plugin --from-file=config.yaml --dry-run=client -oyaml > pve-csi-secret.yaml
```

```shell
kubeseal -o yaml < pve-csi-secret.yaml > infra/storage/proxmox-csi/proxmox-csi-secret.yaml
```

```shell
kubectl apply -k infra/storage/proxmox-csi
```

```shell
kubectl get csistoragecapacities -ocustom-columns=CLASS:.storageClassName,AVAIL:.capacity,ZONE:.nodeTopology.matchLabels -A
```

* Create cluster in Proxmox (one node is fine?)
* Manually label node (instead of Proxmox CCM)

## Plex

```shell
kubectl apply -k apps/media/plex
```
