curl -O https://repo.mongodb.org/apt/ubuntu/dists/jammy/mongodb-org/8.0/multiverse/binary-amd64/mongodb-org-server_8.0.13_amd64.deb
sudo dpkg -i mongodb-org-server_8.0.13_amd64.deb
rm mongodb-org-server_8.0.13_amd64.deb
curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | sudo gpg -o /etc/apt/trusted.gpg.d/mongodb-server-8.0.gpg --dearmor && echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/8.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list && sudo apt update && sudo apt install mongodb-org -y

