# Install Ansible:

brew install ansible

# Upgrade all Oqulabs servers:

ansible-playbook -i inventory upgrade_oqulabs.yml -v

# Upgrade only one server:

ansible-playbook -i inventory upgrade_oqulabs.yml --limit main.oqulabs.kz -v

