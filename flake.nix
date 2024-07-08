{
  description = "Homelab";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        # Define a list of packages that are not compatible with macOS
        linuxOnlyPackages = [
          pkgs.iproute2
          pkgs.libisoburn
        ];

        # Function to filter out Linux-only packages on macOS
        filterLinuxPackages = list:
          if pkgs.stdenv.isDarwin
          then builtins.filter (p: !(builtins.elem p linuxOnlyPackages)) list
          else list;

      in
      with pkgs;
      {
        devShells.default = mkShell {
          packages = filterLinuxPackages [
            ansible
            ansible-lint
            bmake
            diffutils
            docker
            docker-compose_1 # TODO upgrade to version 2
            dyff
            git
            go
            gotestsum
            jq
            k9s
            kanidm
            kube3d
            kubectl
            kubernetes-helm
            kustomize
            neovim
            openssh
            p7zip
            pre-commit
            shellcheck
            terraform # TODO replace with OpenTofu, Terraform is no longer FOSS
            yamllint

            (python3.withPackages (p: with p; [
              jinja2
              kubernetes
              mkdocs-material
              netaddr
              pexpect
              rich
            ]))
          ];

          shellHook = if stdenv.isDarwin then ''
            echo "Note: Some Linux-specific tools (iproute2, libisoburn) are not available on macOS."
            echo "Consider using Docker or a VM for full Linux environment if needed."
          '' else "";
        };
      }
    );
}
