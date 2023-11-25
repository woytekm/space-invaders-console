#!/opt/local/Library/Frameworks/Python.framework/Versions/3.6/bin/python3.6

import functools
import time
import curses 
import sys
import random
import uuid
import re
import os
from pynput import keyboard

version = "0.1"

debug = False

G_keymap = {"KEY_LEFT": "Key.ctrl", "KEY_RIGHT": "Key.cmd", "KEY_FIRE":"Key.alt_r","KEY_QUIT":"\'q\'"}
G_pressed_keys = { G_keymap["KEY_LEFT"]:False, G_keymap["KEY_RIGHT"]:False, G_keymap["KEY_FIRE"]:False, G_keymap["KEY_QUIT"]:False }

#  various tool functions

def is_ssh_session():
    return 'SSH_CLIENT' in os.environ or 'SSH_TTY' in os.environ

def list_to_str(s): 
    str1 = functools.reduce(lambda x,y : x+y, s)
    return str1
     
def debug_msg(debug_str,debug_state=True):
    if debug_state:
      with open('debug.log', 'a') as f:
        f.write(debug_str)

def on_key_press(key):
  debug_msg(f"pressed key {key}\n",debug)
  if(str(key) in G_pressed_keys):
    G_pressed_keys[str(key)] = True
 
def on_key_release(key):
  debug_msg(f"released key {key}\n",debug)
  if(str(key) in G_pressed_keys):
    G_pressed_keys[str(key)] = False

def flip_direction(direction):
 if direction == '+':
   return '-'
 else:
   return '+'

def clear_rect(x1,x2,y1,y2,screen):
 for i in range(y1,y2):
   for j in range(x1-1,x2+1):
      screen[i][j] = ' '

def draw_resource(resource,x1,y1,x_rect,y_rect,screen):
 idx = 0
 for i in range(y1,y1+y_rect):
  for j in range(x1,x1+x_rect):
    screen[i][j] = resource[idx]
    idx += 1

# objects

class Arena:

  def __init__(self,height,width,scr):
     self.width = width
     self.height = height
     self.rows = []
     self.color_map = []
     self.items = []
     self.curses_scr = scr
     self.default_color_pair = 0

     for i in range(self.height):
       screen_row = []
       for i in range(self.width):
         screen_row.append(' ')
       self.rows.append(screen_row)

     for i in range(self.height):
       color_map_row = []
       for i in range(self.width):
         color_map_row.append(self.default_color_pair)
       self.color_map.append(color_map_row)

     self.curses_scr.clear()
     self.curses_scr.refresh()

  def clear(self):
     for row in self.rows:
       row.clear()
       for i in range(self.width):
         row.append(' ')

  def update_status_bar(self,text):
     offset = int(len(text)/2) * -1
     for char in text:
      self.rows[self.height-1][int(self.width/2)+offset] = char
      offset += 2
	 
  def world_time_step(self,key_event,phase_timer):
     for i in self.items:
       i.item_step(self.items,key_event,phase_timer)
       i.item_update_screen(self.rows,self.color_map)

     enemy_ships_alive = False

     for i,item in enumerate(self.items):
       if item.object_type == "EnemyShip":
          enemy_ships_alive = True

       if item.event == "died":
         debug_msg(f"world: {item.uuid}: remove dead item\n",debug)
         if self.items[i].object_type == "HeroShip":
           self.update_status_bar("GAME OVER")
         del self.items[i]

     if not enemy_ships_alive:
       self.update_status_bar("YOU WIN!")
 
  def redraw(self):
     for i in range(self.height):
       #row_str = list_to_str(self.rows[i])
       for j,char in enumerate(self.rows[i]):
         self.curses_scr.addstr(i, j, char, curses.color_pair(self.color_map[i][j])) 
       #self.curses_scr.addstr(i, 0, row_str, curses.color_pair(1))
     self.curses_scr.refresh()    


class WorldItem():

  def __init__(self,x,y,bound_y,bound_x,rand=True):

     if rand:
       self.x_pos = random.randint(0,bound_x-1)
       self.y_pos = random.randint(0,bound_y-1)
     else:
       self.x_pos = x
       self.y_pos = y

     self.bound_x = bound_x
     self.bound_y = bound_y
     self.old_x_pos = self.x_pos
     self.old_y_pos = self.y_pos
     self.uuid = uuid.uuid4()
     self.color_pair = 0


class Brick(WorldItem):

  def __init__(self,x,y,bound_x,bound_y,rand=True):
     super().__init__(x,y,bound_y,bound_x,rand)
     self.object_type = "Brick"
     self.event = "normal"
     self.color_pair = 1

  def item_step(self,other_items,key_event,phase_timer):

     if self.event == "normal":
       pass
     elif self.event == "died":
       return

     for other_item in other_items:
         if other_item.uuid != self.uuid:
           if (other_item.x_pos == self.x_pos) and (other_item.y_pos == self.y_pos):
               debug_msg(f"item Brick {self.uuid} crashed with another item \n",debug)
               if other_item.object_type == "EnemyMissile":
                 self.event = "died"
                 debug_msg(f"item Brick {self.uuid} died due to hit with EnemyMissile item {other_item.uuid}\n",debug)
               elif other_item.object_type == "HeroMissile":
                 self.event = "died"
                 debug_msg(f"item Brick {self.uuid} died due to hit with HeroMissile item {other_item.uuid}\n",debug)

  def item_update_screen(self,screen_arr,color_map):
     if self.event == "normal":
       screen_arr[self.old_y_pos][self.old_x_pos] = ' '
       screen_arr[self.y_pos][self.x_pos] = '#'
       color_map[self.old_y_pos][self.old_x_pos] = 0  # assumed default color pair = 0
       color_map[self.y_pos][self.x_pos] = self.color_pair
     elif self.event == "died":
       screen_arr[self.y_pos][self.x_pos] = ' '
       color_map[self.y_pos][self.x_pos] = 0   # assumed default color pair = 0



class HeroShip(WorldItem):

  def __init__(self,x,y,bound_y,bound_x,rand=True):
     super().__init__(x,y,bound_y,bound_x,rand)
     self.object_type = "HeroShip"
     self.event = "normal"
     self.object_rect_x = 5
     self.object_rect_y = 3
     self.shot_delay = 8
     self.shot_delay_ctr = 0
 
     self.resources = {}

     self.resources['normal'] = [' ',' ','T',' ',' ','|','M','M','M','|','|','W','W','W','|']
     self.resources['explode-1'] = [' ',' ','T',' ',' ','|','x','x','x','|','|','W','x','W','|']
     self.resources['explode-2'] = ['','\\','|','/',' ','-','-','x','-','-',' ','/','|','\\',' ']
     self.resources['explode-3'] = ['*','*','*','*','*','*','*','*','*','*','*','*','*','*','*']
     self.resources['explode-4'] = [' ','*','*','*',' ','*','*','*','*','*',' ','*','*','*',' ']
     self.resources['explode-5'] = [' ',' ','*',' ',' ',' ','*','*','*',' ',' ',' ','*',' ',' ']
     self.resources['explode-6'] = [' ',' ',' ',' ',' ',' ',' ','*',' ',' ',' ',' ',' ',' ',' ']
 
 
  def item_update_screen(self,screen_arr,color_map):

     clear_rect(self.old_x_pos,self.old_x_pos+self.object_rect_x,self.old_y_pos,self.old_y_pos+self.object_rect_y,screen_arr)

     if self.event == "normal":
       draw_resource(self.resources['normal'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-1":
       draw_resource(self.resources['explode-1'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-2":
       draw_resource(self.resources['explode-2'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-3":
       draw_resource(self.resources['explode-3'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-4":
       draw_resource(self.resources['explode-4'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-5":
       draw_resource(self.resources['explode-5'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-6":
       draw_resource(self.resources['explode-6'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "died":
       clear_rect(self.x_pos,self.y_pos,self.x_pos+self.object_rect_x,self.y_pos+self.object_rect_y,screen_arr)


  def item_step(self,other_items,pressed_keys,phase_timer):

     self.shot_delay_ctr += 1
     if self.shot_delay_ctr >= self.shot_delay:
       self.shot_delay_ctr = 0

     if self.event == "normal":
       pass
     elif self.event == "explode-1":
       self.event = "explode-2"
       return
     elif self.event == "explode-2":
       self.event = "explode-3"
       return
     elif self.event == "explode-2":
       self.event = "explode-3"
       return
     elif self.event == "explode-3":
       self.event = "explode-4"
       return
     elif self.event == "explode-4":
       self.event = "explode-5"
       return
     elif self.event == "explode-5":
       self.event = "explode-6"
       return
     elif self.event == "explode-6":
       self.event = "died"
       return

     if pressed_keys[G_keymap["KEY_LEFT"]] == True:     # arrow left
       if self.x_pos > 0:
         self.old_x_pos = self.x_pos
         self.x_pos -= 1
     elif pressed_keys[G_keymap["KEY_RIGHT"]] == True:   # arrow right
       if self.x_pos+self.object_rect_x < self.bound_x:
         self.old_x_pos = self.x_pos
         self.x_pos += 1 
     if pressed_keys[G_keymap["KEY_FIRE"]] == True:    # space bar / fire
       other_items.append(HeroMissile(self.x_pos+2,self.y_pos-1,self.bound_x,self.bound_y,False))
     
     for other_item in other_items:
       if other_item.uuid != self.uuid:
         if (other_item.x_pos == self.x_pos) and (other_item.y_pos == self.y_pos):
           debug_msg(f"item HeroShip {self.uuid} crashed with another item {other_item.object_type} {other_item.uuid}\n",debug)
         if other_item.object_type == "EnemyMissile" and (other_item.x_pos >= self.x_pos) and (other_item.x_pos <= (self.x_pos + self.object_rect_x)) and (other_item.y_pos == self.y_pos):
              self.event = "explode-1"
              debug_msg(f"item HeroShip {self.uuid} event {self.event}\n",debug)



class EnemyShip(WorldItem):

  def __init__(self,x,y,bound_y,bound_x,transform_period=20,rand=True):
     super().__init__(x,y,bound_y,bound_x,rand)
     self.object_type = "EnemyShip"
     self.event = "move-1"
     self.object_rect_x = 5
     self.object_rect_y = 3
     self.transform_timer = 0
     self.transform_period = transform_period
     self.direction = 'R'

     self.resources = {}

     self.resources['move-1'] = [' ','\\','^','/',' ',' ','/','X','\\',' ','/',' ','V',' ','\\']
     self.resources['move-2'] = [' ',']','^','[',' ',' ','/','X','\\',' ',']',' ','V',' ','[']
     self.resources['explode-1'] = ['*','*','*','*','*','*','*','*','*','*','*','*','*','*','*']
     self.resources['explode-2'] = ['','\\','|','/',' ','-','-','x','-','-',' ','/','|','\\',' ']
     self.resources['explode-3'] = ['*','*','*','*','*','*','*','*','*','*','*','*','*','*','*']
     self.resources['explode-4'] = [' ','*','*','*',' ','*','*','*','*','*',' ','*','*','*',' ']
     self.resources['explode-5'] = [' ',' ','*',' ',' ',' ','*','*','*',' ',' ',' ','*',' ',' ']
     self.resources['explode-6'] = [' ',' ',' ',' ',' ',' ',' ','*',' ',' ',' ',' ',' ',' ',' ']
     self.resources['explode-7'] = [' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ',' ']

  def item_update_screen(self,screen_arr,color_map):

     clear_rect(self.old_x_pos,self.old_x_pos+self.object_rect_x,self.old_y_pos,self.old_y_pos+self.object_rect_y,screen_arr)
     clear_rect(self.x_pos,self.x_pos+self.object_rect_x,self.y_pos,self.y_pos+self.object_rect_y,screen_arr)

     if self.event == "move-1":
       draw_resource(self.resources['move-1'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     if self.event == "move-2":
       draw_resource(self.resources['move-2'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-1":
       draw_resource(self.resources['explode-1'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-2":
       draw_resource(self.resources['explode-2'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-3":
       draw_resource(self.resources['explode-3'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-4":
       draw_resource(self.resources['explode-4'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-5":
       draw_resource(self.resources['explode-5'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-6":
       draw_resource(self.resources['explode-6'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)

     elif self.event == "explode-7":
       draw_resource(self.resources['explode-7'],self.x_pos,self.y_pos,self.object_rect_x,self.object_rect_y,screen_arr)
       
     elif self.event == "died":
       clear_rect(self.x_pos,self.x_pos+self.object_rect_x,self.y_pos,self.y_pos+self.object_rect_y,screen_arr)


  def item_step(self,other_items,key_event,phase_timer):

     if self.event != 'died' or not re.match("explode",self.event):
      for other_item in other_items:
        if other_item.uuid != self.uuid:
          if(other_item.x_pos >= self.x_pos) and (other_item.x_pos <= self.x_pos + self.object_rect_x) and (other_item.y_pos == (self.y_pos + self.object_rect_y)):
            debug_msg(f"item EnemyShip {self.uuid} crashed with another item {other_item.object_type} {other_item.uuid}\n",debug)
            if other_item.object_type == "HeroMissile":
               self.event = "explode-1"
               debug_msg(f"item HeroShip {self.uuid} event {self.event} due to hit by HeroMissile {other_item.uuid}\n",debug)
               return

     should_shot = random.randint(0,50)

     if should_shot == 5:
       other_items.append(EnemyMissile(self.x_pos+int(self.object_rect_x/2),self.y_pos+self.object_rect_y,self.bound_x,self.bound_y,False))

     if self.x_pos + self.object_rect_x == self.bound_x-1:
       for item in other_items:
        if item.object_type == "EnemyShip":
          item.direction = 'L'
     if self.x_pos == 1:
       for item in other_items:
        if item.object_type == "EnemyShip": 
          item.direction = 'R'

     if self.event == "move-1":
       self.transform_timer += 1
       if self.transform_timer > self.transform_period:
         self.transform_timer = 0
         self.event = "move-2"
         if self.direction == 'R':
          self.old_x_pos = self.x_pos
          self.x_pos += 1
         else:
          self.old_x_pos = self.x_pos
          self.x_pos -= 1

     if self.event == "move-2":
       self.transform_timer += 1
       if self.transform_timer > self.transform_period:
         self.transform_timer = 0
         self.event = "move-1"
         if self.direction == 'R':
          self.old_x_pos = self.x_pos
          self.x_pos += 1
         else:
          self.old_x_pos = self.x_pos
          self.x_pos -= 1
     elif self.event == "explode-1":
       self.event = "explode-2"
     elif self.event == "explode-2":
       self.event = "explode-3"
     elif self.event == "explode-2":
       self.event = "explode-3"
     elif self.event == "explode-3":
       self.event = "explode-4"
     elif self.event == "explode-4":
       self.event = "explode-5"
     elif self.event == "explode-5":
       self.event = "explode-6"
     elif self.event == "explode-6":
       self.event = "explode-7"
     elif self.event == "explode-7":
       self.event = "died"

     if phase_timer == 400:
       self.old_y_pos = self.y_pos
       self.y_pos += 2
     if phase_timer == 900:
       self.old_y_pos = self.y_pos
       self.y_pos += 2     
     if phase_timer == 1100:
       self.old_y_pos = self.y_pos
       self.y_pos += 2
     if phase_timer == 1500:
       self.old_y_pos = self.y_pos
       self.y_pos += 2  
     if phase_timer == 1750:
       self.old_y_pos = self.y_pos
       self.y_pos += 2
     if phase_timer == 1800:
       self.old_y_pos = self.y_pos
       self.y_pos += 2
     if phase_timer == 1850:
       self.old_y_pos = self.y_pos
       self.y_pos += 2
     if phase_timer == 1900:
       self.old_y_pos = self.y_pos
       self.y_pos += 2
     if phase_timer == 1950:
       self.old_y_pos = self.y_pos
       self.y_pos += 2
     if phase_timer == 2000:
       self.old_y_pos = self.y_pos
       self.y_pos += 2
     if phase_timer == 2050:
       self.old_y_pos = self.y_pos
       self.y_pos += 2


class HeroMissile(WorldItem):
  
  def __init__(self,x,y,bound_x,bound_y,rand=True):
     super().__init__(x,y,bound_y,bound_x,rand)
     self.object_type = "HeroMissile"
     self.event = "normal"
     self.color_pair = 2

  def item_update_screen(self,screen_arr,color_map):
     if self.event == "normal":
       screen_arr[self.old_y_pos][self.old_x_pos] = ' '
       screen_arr[self.y_pos][self.x_pos] = '|'
       color_map[self.old_y_pos][self.old_x_pos] = 0
       color_map[self.y_pos][self.x_pos] = self.color_pair
     elif self.event == "died":
       screen_arr[self.y_pos][self.x_pos] = ' '
       color_map[self.y_pos][self.x_pos] = 0
     elif self.event == "explode-1":
       screen_arr[self.y_pos][self.x_pos] = '*'
       screen_arr[self.y_pos-1][self.x_pos-1] = '\\'
       screen_arr[self.y_pos+1][self.x_pos+1] = '\\'
       screen_arr[self.y_pos-1][self.x_pos+1] = '/'
       screen_arr[self.y_pos+1][self.x_pos-1] = '/'
     elif self.event == "explode-2":
       screen_arr[self.y_pos][self.x_pos] = '*'
       screen_arr[self.y_pos-1][self.x_pos-1] = '#'
       screen_arr[self.y_pos+1][self.x_pos+1] = '#'
       screen_arr[self.y_pos-1][self.x_pos+1] = '#'
       screen_arr[self.y_pos+1][self.x_pos-1] = '#'
       screen_arr[self.y_pos][self.x_pos-1] = '#'
       screen_arr[self.y_pos][self.x_pos+1] = '#'
       screen_arr[self.y_pos-1][self.x_pos] = '#'
       screen_arr[self.y_pos+1][self.x_pos] = '#'
     elif self.event == "explode-3":
       screen_arr[self.y_pos][self.x_pos] = '#'
       screen_arr[self.y_pos-1][self.x_pos-1] = '*'
       screen_arr[self.y_pos+1][self.x_pos+1] = '*'
       screen_arr[self.y_pos-1][self.x_pos+1] = '*'
       screen_arr[self.y_pos+1][self.x_pos-1] = '*'
       screen_arr[self.y_pos][self.x_pos-1] = '*'
       screen_arr[self.y_pos][self.x_pos+1] = '*'
       screen_arr[self.y_pos-1][self.x_pos] = '*'
       screen_arr[self.y_pos+1][self.x_pos] = '*'
     elif self.event == "explode-4":
       screen_arr[self.y_pos][self.x_pos] = '#'
       screen_arr[self.y_pos-1][self.x_pos-1] = '*'
       screen_arr[self.y_pos+1][self.x_pos+1] = '*'
       screen_arr[self.y_pos-1][self.x_pos+1] = '*'
       screen_arr[self.y_pos+1][self.x_pos-1] = '*'
       screen_arr[self.y_pos][self.x_pos-1] = ' '
       screen_arr[self.y_pos][self.x_pos+1] = ' '
       screen_arr[self.y_pos-1][self.x_pos] = ' '
       screen_arr[self.y_pos+1][self.x_pos] = ' '
     elif self.event == "explode-5":
       screen_arr[self.y_pos][self.x_pos] = ' '
       screen_arr[self.y_pos-1][self.x_pos-1] = ' '
       screen_arr[self.y_pos+1][self.x_pos+1] = ' '
       screen_arr[self.y_pos-1][self.x_pos+1] = ' '
       screen_arr[self.y_pos+1][self.x_pos-1] = ' '
       screen_arr[self.y_pos][self.x_pos-1] = ' '
       screen_arr[self.y_pos][self.x_pos+1] = ' '
       screen_arr[self.y_pos-1][self.x_pos] = ' '
       screen_arr[self.y_pos+1][self.x_pos] = ' '

  def item_step(self,other_items,key_event,phase_timer):

     if self.event == "normal":
       self.old_y_pos = self.y_pos
       self.y_pos -= 1
     elif self.event == "explode-1":
       self.event = "explode-2"
       return
     elif self.event == "explode-2":
       self.event = "explode-3"
       return
     elif self.event == "explode-2":
       self.event = "explode-3"
       return
     elif self.event == "explode-3":
       self.event = "explode-4"
       return
     elif self.event == "explode-4":
       self.event = "explode-5"
       return
     elif self.event == "explode-5":
       self.event = "died"
       return
     
     for other_item in other_items:
       if other_item.uuid != self.uuid:
         if (other_item.y_pos == self.y_pos) and (other_item.x_pos == self.x_pos):
            debug_msg(f"item HeroMissile {self.uuid} event explode due to hit another item {other_item.object_type} {other_item.uuid}\n",debug)
            self.event = "explode-1"

     if self.y_pos == 1:
            debug_msg(f"item HeroMissile {self.uuid} event explode\n",debug)
            self.event = "explode-1"


class EnemyMissile(WorldItem):

  def __init__(self,x,y,bound_x,bound_y,rand=True):
     super().__init__(x,y,bound_y,bound_x,rand)
     self.object_type = "EnemyMissile"
     self.event = "normal"

  def item_update_screen(self,screen_arr,color_map):
     if self.event == "normal":
       screen_arr[self.old_y_pos][self.old_x_pos] = ' '
       screen_arr[self.y_pos][self.x_pos] = '|'
     elif self.event == "died":
       screen_arr[self.y_pos][self.x_pos] = ' '
     elif self.event == "explode-1":
       screen_arr[self.y_pos][self.x_pos] = '*'
       screen_arr[self.y_pos-1][self.x_pos-1] = '\\'
       screen_arr[self.y_pos+1][self.x_pos+1] = '\\'
       screen_arr[self.y_pos-1][self.x_pos+1] = '/'
       screen_arr[self.y_pos+1][self.x_pos-1] = '/'
     elif self.event == "explode-2":
       screen_arr[self.y_pos][self.x_pos] = '*'
       screen_arr[self.y_pos-1][self.x_pos-1] = '#'
       screen_arr[self.y_pos+1][self.x_pos+1] = '#'
       screen_arr[self.y_pos-1][self.x_pos+1] = '#'
       screen_arr[self.y_pos+1][self.x_pos-1] = '#'
       screen_arr[self.y_pos][self.x_pos-1] = '#'
       screen_arr[self.y_pos][self.x_pos+1] = '#'
       screen_arr[self.y_pos-1][self.x_pos] = '#'
       screen_arr[self.y_pos+1][self.x_pos] = '#'
     elif self.event == "explode-3":
       screen_arr[self.y_pos][self.x_pos] = '#'
       screen_arr[self.y_pos-1][self.x_pos-1] = '*'
       screen_arr[self.y_pos+1][self.x_pos+1] = '*'
       screen_arr[self.y_pos-1][self.x_pos+1] = '*'
       screen_arr[self.y_pos+1][self.x_pos-1] = '*'
       screen_arr[self.y_pos][self.x_pos-1] = '*'
       screen_arr[self.y_pos][self.x_pos+1] = '*'
       screen_arr[self.y_pos-1][self.x_pos] = '*'
       screen_arr[self.y_pos+1][self.x_pos] = '*'
     elif self.event == "explode-4":
       screen_arr[self.y_pos][self.x_pos] = '#'
       screen_arr[self.y_pos-1][self.x_pos-1] = '*'
       screen_arr[self.y_pos+1][self.x_pos+1] = '*'
       screen_arr[self.y_pos-1][self.x_pos+1] = '*'
       screen_arr[self.y_pos+1][self.x_pos-1] = '*'
       screen_arr[self.y_pos][self.x_pos-1] = ' '
       screen_arr[self.y_pos][self.x_pos+1] = ' '
       screen_arr[self.y_pos-1][self.x_pos] = ' '
       screen_arr[self.y_pos+1][self.x_pos] = ' '
     elif self.event == "explode-5":
       screen_arr[self.y_pos][self.x_pos] = ' '
       screen_arr[self.y_pos-1][self.x_pos-1] = ' '
       screen_arr[self.y_pos+1][self.x_pos+1] = ' '
       screen_arr[self.y_pos-1][self.x_pos+1] = ' '
       screen_arr[self.y_pos+1][self.x_pos-1] = ' '
       screen_arr[self.y_pos][self.x_pos-1] = ' '
       screen_arr[self.y_pos][self.x_pos+1] = ' '
       screen_arr[self.y_pos-1][self.x_pos] = ' '
       screen_arr[self.y_pos+1][self.x_pos] = ' '

  def item_step(self,other_items,key_event,phase_timer):

     if self.event == "normal":

       self.old_y_pos = self.y_pos
       self.y_pos += 1

     elif self.event == "explode-1":
       self.event = "explode-2"
       return
     elif self.event == "explode-2":
       self.event = "explode-3"
       return
     elif self.event == "explode-2":
       self.event = "explode-3"
       return
     elif self.event == "explode-3":
       self.event = "explode-4"
       return
     elif self.event == "explode-4":
       self.event = "explode-5"
       return
     elif self.event == "explode-5":
       self.event = "died"
       return

     for other_item in other_items:
       if other_item.uuid != self.uuid:
         if (other_item.x_pos == self.x_pos) and (other_item.y_pos == self.y_pos) and other_item.object_type != "Ship":
            debug_msg(f"item EnemyMissile {self.uuid} event explode due to hit anoter item {other_item.uuid}\n",debug)
            self.event = "explode-1"

     if self.y_pos == self.bound_y-3:
            debug_msg(f"item EnemyMissile {self.uuid} event explode\n",debug)
            self.event = "explode-1"



# build barriers

def add_barrier(x,y,scr,height,width):

  for xpos in range(x+1,x+6):
   scr.items.append(Brick(xpos,y,height,width,False))
  
  for xpos in range(x,x+7):
   scr.items.append(Brick(xpos,y+1,height,width,False))

  for xpos in range(x,x+7):
   scr.items.append(Brick(xpos,y+2,height,width,False))

  for xpos in range(x,x+7):
   scr.items.append(Brick(xpos,y+3,height,width,False))



def add_enemy_ship_wave(startx,starty,ships,world,world_height,world_width,shot_speed):
  
 x,y = startx,starty
 space = 10

 for i in range(ships):
   world.items.append(EnemyShip(x,y,world_height,world_width,shot_speed,False))
   x += space


# main program executed through curses wrapper

def main(stdscr):

  curses.cbreak()
  curses.noecho()

  # color pair 1: Bricks
  curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
  # color pair 2: HeroMissile
  curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)

  stdscr.nodelay(1)

  arena_height = term_size.lines
  arena_width = 115
  world_time_base = 0.04
  game_phase_timer = 0
  enemy_shot_speed = 6

  scr1 = Arena(arena_height,arena_width,stdscr)

  barrier_spacer = 30
  x = 10

  for i in range(4):
    add_barrier(x,arena_height - 10,scr1,arena_height,arena_width)
    x += barrier_spacer

  scr1.items.append(HeroShip(50,arena_height - 5,arena_height,arena_width,False)) 

  add_enemy_ship_wave(10,1,10,scr1,arena_height,arena_width,enemy_shot_speed)
  add_enemy_ship_wave(15,6,9,scr1,arena_height,arena_width,enemy_shot_speed)
  add_enemy_ship_wave(10,12,10,scr1,arena_height,arena_width,enemy_shot_speed)
  add_enemy_ship_wave(15,18,9,scr1,arena_height,arena_width,enemy_shot_speed)

  listener = keyboard.Listener(on_release = on_key_release,on_press = on_key_press)
  listener.start()

  while True:
   game_phase_timer += 1
   time.sleep(world_time_base)

   if(game_phase_timer > 1000):
     world_time_base = 0.03
   if(game_phase_timer > 2000):
     world_time_base = 0.02
   if(game_phase_timer > 3000):
     world_time_base = 0.01

   if G_pressed_keys[G_keymap["KEY_QUIT"]] == True:
     stdscr.getch()
     return

   scr1.world_time_step(G_pressed_keys,game_phase_timer)
   scr1.redraw()


# actual main code 

term_size = os.get_terminal_size()

if(term_size.columns < 120) or (term_size.lines < 40):
  print(f"Error: this game needs at least 45 lines x 120 column terminal.You have {term_size.lines}x{term_size.columns}.\n")
  sys.exit()

if is_ssh_session():
  print("Error: this game will not work properly over SSH session.")
  sys.exit()

curses.wrapper(main)


