#!/bin/bash
sudo systemctl restart coachai@{1..2}
sudo systemctl restart coachai_worker@{1..2}