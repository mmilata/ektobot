#!/bin/sh

export ANSIBLE_CONFIG=ansible.cfg

ansible-playbook site.yml "$@"
