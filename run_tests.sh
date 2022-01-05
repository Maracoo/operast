#!/usr/bin/env bash

pytest \
  --cov="operast/" \
  --cov-branch \
  --cov-report=term \
  --cov-report=html \
  "tests/"
