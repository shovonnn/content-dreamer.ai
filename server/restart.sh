#!/bin/bash
sudo systemctl restart content-dreamer-server@{1..2}
sudo systemctl restart content-dreamer-worker@{1..3}