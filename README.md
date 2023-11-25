I wrote this game during Python course in spare time between execrices.

It is written in Python 3.6 and uses curses library to display animated semigraphics in shell terminal/cmd window. Pynput library is used for keyboard monitoring.
It will work only on console sessions, won't work properly through SSH session (pynput keyboard monitoring won't work over SSH). 

On more recent OS X versions i have noticed that pynput has some problems with key monitoring, and only keys which work are: CTRL, Option, Command and Shift. 
This seems to be a known problem with no fix provided so far. Adding process to trusted in Accessibility Clients and Keyboard OS X settings does not help.
The game can still be played using mentioned keys, but not so comfortably as with classic "cursor keys + spacebar" setup.

Key remapping can be done by editing G_keymap variable.

Only tested on OS X at this moment. 

![](https://github.com/woytekm/space-invaders-console/blob/main/Game.gif)

