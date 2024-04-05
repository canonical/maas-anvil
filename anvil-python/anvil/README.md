# Anvil

```bash
# $ cat resnap.sh

#!/bin/bash

sudo snap remove anvil
sudo snap remove juju
sudo remove-juju-services

sudo rm -rf /var/lib/juju
sudo rm -rf /usr/lib/juju
sudo rm -rf /etc/init/juju*
sudo rm -rf /var/lib/juju
sudo rm -rf /lib/systemd/system/juju*
sudo rm -rf /run/systemd/units/invocation:juju*
sudo rm -rf /etc/systemd/system/juju*

rm -rf .local/share/juju
rm -rf ~/.ssh/id_rsa*

sudo snap install --dangerous anvil.snap

anvil --help
anvil prepare-node-script | bash -x

sudo snap connect anvil:dot-local-share-juju
sudo snap connect anvil:dot-config-anvil
sudo snap connect anvil:juju-bin juju:juju-bin

anvil cluster bootstrap --role database --role region --role agent --role haproxy --accept-defaults
```

## Remaining items

- [ ] plugins
- [ ] resize
- [ ] refresh
- [ ] configure
- [ ] unit tests
- [ ] inspect
