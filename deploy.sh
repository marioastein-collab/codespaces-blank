#!/bin/bash
git add .
git commit -m "Auto deploy on $(date +%Y-%m-%d %H:%M:%S)"
git push origin main
