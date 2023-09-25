➕ root['stages']['deploy'] -> `Kubernetes Deploy`

➕ root['stages']['postdeploy'] -> `Cypress Test`

➕ root['deployment']['traefik']['hosts'] -> 
```
  - host:
      all: "Host(`some.other.host.com`)"
    servicePort: 4091
    priority: 1000
    whitelists:
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

➖ root['deployment']['traefik']['host'] -> 
```
all: "Host(`some.other.host.com`)"
servicePort: 4091
priority: 1000
```
  root['stages']['test']: Docker Test