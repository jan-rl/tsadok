# This module contains the Tile class 
#
#
import libtcodpy as libtcod

class Tile:
    #a tile of the map and its properties
    def __init__(self, blocked, block_sight = None, type='dummy', name='dummy' ):
        self.blocked = blocked

        #all tiles start unexplored
        self.explored = False

        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight
        
        #self.type = type #terrain options set in make_map() to show different appearance in render_all()
        
        self.name = name
        
        self.trail = False
  
        self.change_type(type)
            
    def change_type(self, type):    
        self.type = type
        
        if type == 'empty': #empty tile
            self.name = 'empty'
            self.char_light = '.'
            self.char_dark = ' '
            self.color_light = 'grey'
            self.color_dark = 'black'
            self.blocked = False
            self.block_sight = False
        
        elif type == 'rubble': #empty tile
            self.name = 'rubble'
            
            i = libtcod.random_get_int(0, 0, 3)
            if i == 1:                
                self.char_light = ','
                
            elif i == 2:                    
                self.char_light = '.'
                
            else:                
                self.char_light = '.'
            
            self.char_dark = ' '
            self.color_light = 'dark grey'
            self.color_dark = 'black'
            self.blocked = False
            self.block_sight = False

        elif type == 'grass':
            self.name = 'grass'
            
            i = libtcod.random_get_int(0, 0, 3)
            if i == 1:                
                self.char_light = ','
                
            elif i == 2:                    
                self.char_light = '.'
                
            else:                
                self.char_light = '.'
               
            i = libtcod.random_get_int(0, 0, 3)
            if i == 1:
                self.color_light = 'lighter green'
            elif i == 2:
                self.color_light = 'light green'
            else:
                self.color_light = 'dark green'
            
            self.char_dark = ' '
            
            self.color_dark = 'black'
            self.blocked = False
            self.block_sight = False
            
        elif type == 'leaf':
            self.name = 'leaf'
            self.char_light = 'o'
            self.char_dark = ' '
            self.color_light = 'green'
            self.color_dark = 'darkest blue'
            self.blocked = False
            self.block_sight = False
            
        elif type == 'rock':
            self.name = 'rock'
            self.char_light = '[U+25B2]'
            self.char_dark = ' '
            self.color_light = 'grey'
            self.color_dark = 'black'
            self.blocked = True
            self.block_sight = True
            
        elif type == 'stone slab':
            self.name = 'stone slab'
            self.char_light = '0'
            self.char_dark = ' '
            self.color_light = 'darker grey'
            self.color_dark = 'darkest blue'
            self.blocked = False
            self.block_sight = False
            
        elif type == 'tree':
            self.name = 'tree'
            self.char_light = '#'
            self.char_dark = ' '
            self.color_light = 'orange'
            self.color_dark = 'darkest blue'
            self.blocked = True
            self.block_sight = False
            
        elif type == 'sky':
            self.name = 'sky'
            self.char_light = '='
            self.char_dark = '='
            self.color_light = 'sky'
            self.color_dark = 'sky'
            self.blocked = False
            self.block_sight = False
            
        elif type == 'air':
            self.name = 'air'
            self.char_light = '='
            self.char_dark = '='
            self.color_light = 'darkest grey'
            self.color_dark = 'darkest grey'
            self.blocked = False
            self.block_sight = False
            
        elif type == 'rock wall':
            self.name = 'wall'
            self.char_light = '#'
            self.char_dark = '#'
            self.color_light = 'grey'
            self.color_dark = 'darkest blue'
            self.blocked = True
            self.block_sight = True
        
        elif type == 'abyss':
            self.name = 'abyss'
            
            list = []
            for i in range(4):
                list.append(str(libtcod.random_get_int(0,0,10)))
            
            s = ''.join(list)
            
            self.char_light = '[U+' +s+']'
            self.char_dark = '#'
            self.color_light = 'purple'
            self.color_dark = 'dark grey'
            self.blocked = False
            self.block_sight = False
        
        elif type == 'granite':
            self.name = 'granite'
            self.char_light = '[U+25B2]'
            self.char_dark = '#'
            self.color_light = 'dark grey'
            self.color_dark = 'darkest blue'
            self.blocked = True
            self.block_sight = True
        
        elif type == 'lava':
            self.name = 'lava'
            self.char_light = '{'
            self.char_dark = '#'
            self.color_light = 'red'
            self.color_dark = 'light red'
            self.blocked = False
            self.block_sight = False
        
        elif type == 'pillar':
            self.name = 'pillar'
            self.char_light = 'o'
            self.char_dark = 'o'
            self.color_light = 'grey'
            self.color_dark = 'darkest blue'
            self.blocked = False
            self.block_sight = False
        
        elif type == 'ropes':
            self.name = 'ropes'
            self.char_light = '-'
            self.char_dark = '-'
            self.color_light = 'darker orange'
            self.color_dark = 'darkest blue'
            self.blocked = False
            self.block_sight = False
            
        elif type == 'bridge':
            self.name = 'bridge'
            self.char_light = '+'
            self.char_dark = '+'
            self.color_light = 'dark orange'
            self.color_dark = 'darkest blue'
            self.blocked = False
            self.block_sight = False
            
        elif type == 'throne':
            self.name = 'throne'
            self.char_light = "\\"
            self.char_dark = '\\'
            self.color_light = 'yellow'
            self.color_dark = 'darkest blue'
            self.blocked = False
            self.block_sight = False
            
        elif type == 'water':
            self.name = 'water'
            self.char_light = '[U+2248]'
            self.char_dark = '[U+2248]'
            self.color_light = 'blue'
            self.color_dark = 'blue'
            self.blocked = False
            self.block_sight = False
        
        elif type == 'door':
            self.name = 'door'
            self.char_light = '+'
            self.char_dark = '+'
            self.color_light = 'orange'
            self.color_dark = 'orange'
            self.blocked = True
            self.block_sight = True
            
        elif type == 'horizontal wall':
            self.name = 'wall'
            self.char_light = '-'
            self.char_dark = '-'
            self.color_light = 'grey'
            self.color_dark = 'darkest blue'
            self.blocked = True
            self.block_sight = True
        
        elif type == 'vertical wall':
            self.name = 'wall'
            self.char_light = '|'
            self.char_dark = '|'
            self.color_light = 'grey'
            self.color_dark = 'darkest blue'
            self.blocked = True
            self.block_sight = True

        else:
            self.name = 'dummy'
            self.char_light = '/'
            self.char_dark = '/'
            self.color_light = 'white'
            self.color_dark = 'blue'
            self.blocked = False
            self.block_sight = False
