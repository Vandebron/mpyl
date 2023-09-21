➕ root['stages']['deploy'] -> `Kubernetes Deploy`

➕ root['stages']['postdeploy'] -> `Cypress Test`

➕ root['deployment']['traefik']['hosts'][0]['whitelists'] -> 
```
pr:
  - "K8s-Test"
  - "VPN"
test:
  - "K8s-Test"
  - "VPN"
acceptance:
  - "VPN"
production:
  - "Outside-World"

```
➖ root['deployment']['namespace'] -> `namespace`

  root['stages']['test']: Docker Test