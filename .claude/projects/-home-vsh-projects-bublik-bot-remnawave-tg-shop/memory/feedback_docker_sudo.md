---
name: docker_sudo
description: User needs sudo for all docker commands on this machine
type: feedback
---

Always prefix docker/docker-compose commands with `sudo` when giving commands to the user.

**Why:** User doesn't have passwordless docker access on this server.
**How to apply:** Every time you provide docker commands for the user to run.
