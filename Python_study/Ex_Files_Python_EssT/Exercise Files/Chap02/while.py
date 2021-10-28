#!/usr/bin/env python3
# Copyright 2009-2017 BHG http://bw.org/


a, b = 0, 1
while b < 1000:
    print(b, end = ' ', flush = True)
    a, b = b, a + b