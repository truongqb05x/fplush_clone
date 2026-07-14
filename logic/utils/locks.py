# -*- coding: utf-8 -*-
import threading

# Lock for shared file access (account.txt, commented.txt, etc)
FILE_LOCK = threading.Lock()
