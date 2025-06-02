# smtp2discord

SMTP server relaying mails to discord

## firewalld settings

- If using `firewalld`, open port `SMTP_PORT`
- In the below example, `SMTP_PORT` is set to `1025`

```sh
sudo firewall-cmd --add-port=1025/tcp --permanent
sudo firewall-cmd --reload
```

## behavior

- When receiving an email to `user@discord.localdomain`, it will be relayed to the Discord channel `user`.
  - channel ID and token are set in `discord.json`.

### discord.json

```json
{
  "user": {
    "chid": "123456789012345678",
    "token": "MTM******"
  },
  "user2": {
    "chid": "2234567890123456789",
    "token": "MTM***********"
  }
}
```

## systemd service

```sh
export __USER__="$( whoami )"
export __DOCKER_COMPOSE_YAML__="$( realpath docker-compose.yaml )"
envsubst < smtp2discord.service | sudo tee /etc/systemd/system/smtp2discord.service

sudo systemctl daemon-reload
sudo systemctl start smtp2discord.service
sudo systemctl enable smtp2discord.service
```
