#!/bin/bash
# Command replay script - Session: 20260126164301
# Generated: 2026-01-31T19:22:19.880965

# [1] 2026-01-26T16:47:12Z
nmap -sV -p- --min-rate 1000 http://testphp.vulnweb.com

# [2] 2026-01-26T16:49:15Z
nmap -sV -p- --min-rate 1000 testphp.vulnweb.com

# [6] 2026-01-26T16:55:13Z
find /usr/share/wordlists -type f -name "*.txt" | head -10

# [8] 2026-01-26T16:55:29Z
feroxbuster --url http://testphp.vulnweb.com

# [10] 2026-01-26T16:56:26Z
curl -s -I http://testphp.vulnweb.com

# [11] 2026-01-26T16:57:33Z
curl -s http://testphp.vulnweb.com

# [12] 2026-01-26T16:57:41Z
curl -s http://testphp.vulnweb.com/login.php

