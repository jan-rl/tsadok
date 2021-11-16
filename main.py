#!/usr/bin/python
# -*- coding: utf-8 -*-
#

import libtcodpy as libtcod
import PyBearLibTerminal as T
import math
import textwrap
import shelve
import time
import random
import re
import string
from collections import defaultdict

#import monsters
import items
import tiles
import timer

#actual size of the window
SCREEN_WIDTH = 50
SCREEN_HEIGHT = 30

#size of the map
MAP_WIDTH = 50
MAP_HEIGHT = 24
MAP_Z = 100

#sizes and coordinates relevant for the GUI
PANEL_HEIGHT = 5
PANEL_WIDTH = SCREEN_WIDTH
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = 11
MSG_WIDTH = PANEL_WIDTH - MSG_X - 10
MSG_HEIGHT = PANEL_HEIGHT-1
INVENTORY_WIDTH = SCREEN_WIDTH - 1

#parameters for dungeon generator
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

FOV_ALGO = 0  #default FOV algorithm
FOV_LIGHT_WALLS = True  #light walls or not

LIMIT_FPS = 20  #20 frames-per-second maximum

FONT_SIZE = 14

connection_points = {

'behind the altar': (MAP_WIDTH/2,MAP_HEIGHT/2,MAP_Z/2) ,
'sewers start': (0,0,0) ,
'sewers end': (0,0,0) ,
'dungeon start': (0,0,0),
'dugeon end': (0,0,0),
'village start': (0,0,0)

}


#---------------------------------------------------------------------------------------------------------
# class Tile: now in tiles.py module

class Rect:
    #a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
        self.w = w
        self.h = h

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        #returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

class Object:
#this is a generic object the player, a monster, an item, the stairs
#it's always represented by a character on screen.
    def __init__(self, x, y, z, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=None):
        self.x = x
        self.y = y
        self.z = z
        self.char = char
        self.base_name = name
        self._color = color
        self.blocks = blocks
        self.always_visible = always_visible
        self.fighter = fighter
        if self.fighter:  #let the fighter component know who owns it
            self.fighter.owner = self

        self.ai = ai
        if self.ai:  #let the AI component know who owns it
            self.ai.owner = self

        self.item = item
        if self.item:  #let the Item component know who owns it
            self.item.owner = self      
            
        self.equipment = equipment
        if self.equipment:  #let the Equipment component know who owns it
            self.equipment.owner = self

            #there must be an Item component for the Equipment component to work properly
            if not self.item:    
                self.item = Item()
                self.item.owner = self
              
        self.fly = False
              
    @property
    def name(self):  #return actual name, by summing up the possible components
        
        nam = self.base_name
       
        return nam
    
    @property
    def color(self):
        color = self._color
        
        if map[self.z+1][self.x][self.y].type == 'water':
            color = 'blue'
        
        return color
    
    @property
    def char(self):
        return self.char
    
    def move(self, dx, dy):
        #check if leaving the map
        if self.x + dx < 0 or self.x + dx >= MAP_WIDTH or self.y + dy < 0 or self.y + dy >= MAP_HEIGHT:
            return
        
        if map[self.z][self.x+dx][self.y+dy].type == 'door':
            for item in self.fighter.inventory:
                if item.name == 'church key':
                    map[self.z][self.x+dx][self.y+dy].change_type('empty')
        
        #move by the given amount, if the destination is not blocked
        if not is_blocked(self.x + dx, self.y + dy, self.z):
            self.x += dx
            self.y += dy
        
        # #falling
        # if map[self.z][self.x][self.y].type == 'sky' or map[self.z][self.x][self.y].type == 'air' or map[self.z][self.x][self.y].type == 'water':
            
            # if get_equipped_in_slot('feet',player):
                # if get_equipped_in_slot('feet',player).owner.base_name == 'winged boots':
                    # if self.fly:
                        # self.fly = False
                        # return
                    # else:
                        # self.fly = True
            
            # for obj in objects[self.z]:
                # if obj.x == player.x and obj.y == player.y and obj.name == 'cloud':
                    # return
            
            # objects[self.z - 1].append(self)
            # objects[self.z].remove(self)
            # self.z -= 1

            # if self == player:
                # initialize_fov()
       
            
    def move_away_from(self, target_x, target_y):
        #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(-dx, -dy)
                        
    def move_towards(self, target_x, target_y):
        # #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        
        ddx = 0 
        ddy = 0
        if dx > 0:
            ddx = 1
        elif dx < 0:
            ddx = -1
        if dy > 0:
            ddy = 1
        elif dy < 0:
            ddy = -1
        if not is_blocked(self.x + ddx, self.y + ddy, self.z):
            self.move(ddx, ddy)
        else:
            if ddx != 0:
                if not is_blocked(self.x + ddx, self.y, self.z):
                    self.move(ddx, 0)
                    return
            if ddy != 0:
                if not is_blocked(self.x, self.y + ddy, self.z):
                    self.move(0, ddy)
                    return
    
    def distance_to(self, other):
        #return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def distance(self, x, y):
        #return the distance to some coordinates
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def send_to_back(self):
        #make this object be drawn first, so all others appear above it if they're in the same tile.
        global objects
        objects[self.z].remove(self)
        objects[self.z].insert(0, self)

    def draw(self):
        #only show if it's visible to the player; or it's set to "always visible" and on an explored tile
        
        #invisible monsters are not drawn
        if self.fighter and self != player:
            if self.fighter.invisible:
                if not player.fighter.see_invisible and not player.fighter.telepathy:
                    return
                elif not player.fighter.see_invisible and player.fighter.telepathy:
                    T.color('white')
                    T.print_(self.x, self.y, 'I')
                    return
                
        if (visible_to_player(self.x,self.y) or
                (self.always_visible and map[self.z][self.x][self.y].explored)):
            T.color(self.color)
            T.print_(self.x, self.y, self.char)
            if self.item:
                self.always_visible = True
        elif self.fighter and player.fighter.telepathy:
            T.color('white')
            T.print_(self.x, self.y, 'I')
            
    def clear(self):
        #erase the character that represents this object
        if visible_to_player(self.x,self.y):
            #libtcod.console_put_char_ex(con, self.x, self.y, '.', libtcod.light_grey, libtcod.black)
            T.color('grey')
            T.print_(self.x, self.y, '.')
            
    def delete(self):
        #easy way to trigger removal from object
        #do not leave its ai
        if self.fighter:
            self.fighter = None
        
        for obj in objects[self.z]:
            if obj.fighter:
                if self in obj.fighter.inventory:
                    obj.fighter.inventory.remove(self)
            if self in objects[self.z]:
                objects[self.z].remove(self)
        self.clear()

class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, damage, armor, wit, strength, spirit, speed=6, xp=0, level=0, hunger=1000, luck=0, temp_invisible=None, weak_spell=None, berserk_potion=None, death_function=None):

        self.base_hp = hp
        self.hp = hp
        
        self.hp_plus = 0 #additional hp granted later in the game
        
        self.base_damage = damage
        self.base_armor = armor
        
        self.base_wit = wit
        self.base_strength = strength
        
        self.base_spirit = spirit
        self.spirit = spirit
        
        self.base_speed = speed
        
        self.xp = xp
        self.level = level
        
        self.hunger = hunger
        
        self.luck = luck
        
        self.temp_invisible = temp_invisible
        self.weak_spell = weak_spell
        
        self.berserk_potion = berserk_potion
        
        self.death_function = death_function
        
        self.skills = []
        self.inventory = []
        self.strike = True
        
    @property
    def max_hp(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = 0 #sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
        hp = self.base_hp + self.hp_plus + bonus
        return hp
    
    @property
    def armor(self):  #return actual defense, by summing up the bonuses from all equipped items
        bonus = sum(equipment.armor_bonus for equipment in get_all_equipped(self.owner))        
        
        ac = self.base_armor + bonus
        
        if 'armor wearer' in self.skills:
            ac = ac * 2    
        return ac

    @property
    def wit(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.wit_bonus for equipment in get_all_equipped(self.owner))
        
        
        if self.weak:
            bonus += 10
        elif self.hunger_status == 'satiated':
            bonus -= 10
        
        wit = self.base_wit + bonus
        if wit < 0:
            wit = 0
            
        return wit
        
    @property
    def strength(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.strength_bonus for equipment in get_all_equipped(self.owner))
        
        if self.weak:
            bonus -= 10
        elif self.hunger_status == 'satiated':
            bonus += 10
        
        str = self.base_strength + bonus
       
        if str < 0:
            str = 0
    
        return str
        
    @property
    def speed(self):
        if self.berserk_potion:
            return self.base_speed - 3
        else:
            return self.base_speed
        
    @property
    def max_spirit(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.spirit_bonus for equipment in get_all_equipped(self.owner))
        
        if self.spirit > self.base_spirit + bonus:
            self.spirit = self.base_spirit + bonus
        
        return self.base_spirit + bonus
            
    def take_damage(self, damage, type): 
        
        #apply damage if possible
        
        start = self.hp
        
        if damage > 0:
            self.hp -= damage
            if self.owner == player:
                message(self.owner.name.capitalize() + ' get ' + str(damage) + ' ' + type + ' damage.', 'red')
            else:
                message(self.owner.name.capitalize() + ' gets ' + str(damage) + ' ' + type + ' damage.', 'red')
       
        if self.hp < start:
            self.strike = not self.strike
            if self.strike:
                c = '/'
            else:
                c = '\\'
            fight_effect(self.owner.x, self.owner.y, 'red', c)
            self.owner.ai.got_damage = True
        else:
            message('No damage done.', 'grey')
            fight_effect(self.owner.x, self.owner.y, 'grey', self.owner.char)
        
        #check for death. if there's a death function, call it
        if self.hp <= 0:
            self.hp = 0
            function = self.death_function
            if function is not None:
                function(self.owner)
        
    
class PlayerAI:
    '''Is actually the one who plays TPB. Needed to be scheduled. Takes keyboard input and calls handle_keys
    Renders screen and exits game, kind of the actual main loop together with play_game.
    '''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.player_reset_coord = (0,0,0)
        self.lava_delay = False
        self.ticker.schedule_turn(self.speed, self)
        
    def take_turn(self):
        '''called by scheduler on the players turn, contains the quasi main loop'''
        global key, mouse, fov_recompute
        action_speed = self.owner.fighter.speed
        
        while True:
            render_all()
            T.refresh()
            
            map[self.owner.z][self.owner.x][self.owner.y].trail = True
            
            key = T.read()
            
            player_action = handle_keys()
            
            if player.x == parameters['throne'][0] and player.y == parameters['throne'][1] and player.z == parameters['throne'][2]:
                player_action = win()
            
            # if player.z == 98:
                # player_action = win()
            
            if map[player.z][player.x][player.y].type == 'rubble' or map[player.z][player.x][player.y].type == 'empty':
                self.player_reset_coord = (player.x,player.y,player.z)
                
            if map[player.z][player.x][player.y].type == 'lava':
                if not self.lava_delay:
                    self.lava_delay = True
                else:
                    objects[self.player_reset_coord[2]].append(player)
                    objects[player.z].remove(player)
                    
                    player.x = self.player_reset_coord[0]
                    player.y = self.player_reset_coord[1]
                    player.z = self.player_reset_coord[2]
                    initialize_fov()
                    self.lava_delay = False
                    message('Ouch!','red')

            if player_action == 'exit' or game_state == 'exit':
                break
                main_menu()
            
            if player_action != 'didnt-take-turn':
                fov_recompute = True
                if not player_action == 'jump':
                    player_fall()
                break
            
        self.ticker.schedule_turn(action_speed, self)
            
def player_fall():
    #falling
    if map[player.z][player.x][player.y].type == 'sky' or map[player.z][player.x][player.y].type == 'air' or map[player.z][player.x][player.y].type == 'water':
        
        if get_equipped_in_slot('feet',player):
            if get_equipped_in_slot('feet',player).owner.base_name == 'winged boots':
                if player.fly:
                    player.fly = False
                    return
                else:
                    player.fly = True
        
        for obj in objects[player.z]:
            if obj.x == player.x and obj.y == player.y and obj.name == 'cloud':
                return
        
        objects[player.z - 1].append(player)
        objects[player.z].remove(player)
        player.z -= 1

        initialize_fov()
   
            
class AIkobold:
    '''AI for a kobold. Schedules the turn depending on speed and decides whether to move or attack.
    '''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
        self.seen_player = False
        self.heard_player = False
        self.got_damage = False
    
    def take_turn(self):
        '''checks whether monster and player are still alive, decides on move or attack'''
        #a basic monster takes its turn.
        monster = self.owner
        
        if not monster.fighter: #most likely because monster is dead
            return
        #stop when the player is already dead
        if game_state == 'dead':
            return
        
        self.speed = monster.fighter.speed
        
        #regenerate(monster)
        breathe(monster)
        #equip_check(monster)                        
        
        if not monster.fighter: #most likely because monster is dead by suffocation
            return
        
        inventory = []
        for i in monster.fighter.inventory:
            inventory.append(i.base_name)
            
        #wait if player on different floor 
        if monster.z != player.z:
            self.ticker.schedule_turn(self.speed, self)            
            return
       
        #--------------------------------------------------
        #hear player
        if monster.distance_to(player) < 3:
            self.heard_player = True
        
        #----------------------------------
        #see player
        #player invisible
        if player.fighter.invisible and not (monster.fighter.see_invisible or monster.fighter.telepathy):
            #can you hear him?
            if self.heard_player: #yes
                
                if libtcod.random_get_int(0,0,100) < 25:
                    pass
                elif monster.distance_to(player) < 3:
                    message(monster.name + ' strikes the air close to you.')
                    self.ticker.schedule_turn(self.speed, self)            
                    return
                elif monster.distance_to(player) > 10:
                    self.seen_player = False
                    self.heard_player = False
                    self.ticker.schedule_turn(self.speed, self)            
                    return
            
            else: #no
                self.ticker.schedule_turn(self.speed, self)            
                return
            
        if visible_to_player(monster.x, monster.y):
            self.seen_player = True
       
        #--------------------------------------------------
        
        if visible_to_player(monster.x, monster.y) or self.seen_player or self.heard_player or self.got_damage:
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                (x,y) = monster.x, monster.y
                monster.move_towards(player.x, player.y)
                if monster.x == x and monster.y == y: #not moved?
                    monster.move(libtcod.random_get_int(0,-1,1), libtcod.random_get_int(0,-1,1)) #try again randomly
                
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
            
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
            
        
class Item:
    #an item that can be picked up and used.
    def __init__(self, charges=0, stackable=False, number = 1, use_function=None, spell_function=None):

        self.stackable = stackable
        self.number = number
        
        self.charges = charges
        self.max_charges = charges
        
        self.use_function = use_function
        self.spell_function = spell_function
        
    def pick_up(self, picker):
        #add to the player's inventory and remove from the map
        if len(picker.fighter.inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', 'red')
        else:
            picker.fighter.inventory.append(self.owner)
            self.owner.x = 0
            self.owner.y = 0
            objects[self.owner.z].remove(self.owner)
            message('You picked up the ' + self.owner.name + '!', 'green')
                        
            #check for stack
            if self.stackable:
                for i in picker.fighter.inventory[:-1]:
                    if i.base_name == self.owner.base_name:
                        i.item.number += self.number
                        del picker.fighter.inventory[-1]
                        return


    def drop(self, dropper):
        #special case: if the object has the Equipment component, dequip it before dropping
        if self.owner.equipment:
            self.owner.equipment.dequip(dropper)

        #add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects[dropper.z].append(self.owner)
        dropper.fighter.inventory.remove(self.owner)
        self.owner.x = dropper.x
        self.owner.y = dropper.y
        self.owner.z = dropper.z
        message(dropper.name + ' dropped a ' + self.owner.name + '.', 'yellow')
        self.owner.send_to_back()
        
    def throw(self, thrower):
        #message('Left-click a target tile to throw the ' + self.owner.name+ ', or right-click to cancel.', 'blue')
        (x, y) = target_tile()
        if x is None or not visible_to_player(x,y): return 'cancelled'
        
        #special case: if the object has the Equipment component, dequip it before throwing
        was_equipped = False
        if self.owner.equipment and self.owner.equipment.is_equipped:
            self.owner.equipment.dequip(thrower)
            was_equipped = True
            
        throw_effect(player.x, player.y, x, y, self.owner.color, self.owner.char)
        
        #add to the map and remove from the player's inventory. also, run animation and place it at the new coordinates
        objects[thrower.z].append(self.owner)
        thrower.fighter.inventory.remove(self.owner)
        self.owner.x = x
        self.owner.y = y
        self.owner.z = thrower.z
        self.owner.send_to_back()
        
        if thrower == player:
            message(thrower.name + ' throw a ' + self.owner.name + '.', 'yellow')
        else:
            message(thrower.name + ' throws a ' + self.owner.name + '.', 'yellow')
        if self.owner.base_name == 'potion of magma': 
            damaged = False
            for i in range(self.number):
                message('The ' + self.owner.name + ' explodes.')
                for obj in objects[thrower.z]:
                    if obj.x == x and obj.y == y and obj.fighter:
                        damage = 20
                        if 'range ranger' in thrower.fighter.skills:
                            damage = damage * 2
                        do_element_damage(thrower, obj, damage, 'fire')
                        damaged = True
                self.owner.delete()
                
                if not damaged:
                    fight_effect(x, y, 'red', '#')
            identify('potion of magma')
        elif self.owner.equipment:
            if self.owner.equipment.damage_bonus and 'range ranger' in thrower.fighter.skills and was_equipped:
                for obj in objects[thrower.z]:
                    if obj.x == x and obj.y == y and obj.fighter:
                        damage = self.owner.equipment.damage_bonus + thrower.fighter.wit / 5
                        do_phys_damage(thrower, obj, damage)
                        if self.owner.equipment.element_damage:
                            do_element_damage(thrower, obj, self.owner.equipment.element_damage, self.owner.equipment.element_enchant)
            
    def use(self, user):
        #cannor read scrolls with sunglasses
        if 'scroll' in self.owner.base_name and user == player and get_equipped_in_slot('eyes', player):
            if get_equipped_in_slot('eyes', player).owner.base_name == 'sunglasses of elemental protection':
                message('You cannot read the '+ self.owner.name + ' with sunglasses on.')
                identify('sunglasses of elemental protection')
                return
        
        #just call the "use_function" if it is defined
        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        
        else:
            if self.use_function(user) != 'cancelled':
                if self.stackable and self.number > 1:
                    self.number -= 1
                elif self.charges:    
                    self.charges -= 1
                    if self.charges == 0:
                        if user.fighter: #dead?
                            user.fighter.inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
                else:
                    if user.fighter: #dead?
                        user.fighter.inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
                
    # def monster_use(self, user, x, y):
        # #just call the "use_function" if it is defined
        # if self.use_function(user) != 'cancelled':
            # if self.stackable and self.number > 1:
                # self.number -= 1
            # elif self.charges:    
                # self.charges -= 1
                # if self.charges == 0:
                    # user.fighter.inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
            # else:    
                # user.fighter.inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
            
def do_phys_damage(source, target, damage):
    #deal
    
    if not target.fighter: #most likely dead
        return
    
    #critical attack
    if libtcod.random_get_int(0,0,100) <= source.fighter.luck / 50:
        damage = damage * 2
        if source == player:
            message(source.name + ' execute a critical attack.')
        else:
            message(source.name + ' executes a critical attack.')
    damage = int(round(damage))
    
    armor = target.fighter.armor
    
    #critical block
    bonus = 0
    if 'armor wearer' in target.fighter.skills:
        bonus = 11
    if libtcod.random_get_int(0,0,100) <= target.fighter.luck / 50 + bonus:
        armor = armor * 2
        if target == player:
            message(target.name + ' perform a critical block.')
        else:
            message(target.name + ' performs a critical block.')
    damage -= armor
    
    target.fighter.take_damage(damage, 'physical')
    
def do_damage(target, damage):
    #unspecific uncounterable damage
    damage = int(round(damage))    
    target.fighter.take_damage(damage, '')    
    
        
class Equipment:
    #an object that can be equipped, yielding bonuses. automatically adds the Item component.
    def __init__(self, slot, max_hp_bonus=0, damage_bonus=0, armor_bonus=0, wit_bonus=0, strength_bonus=0, spirit_bonus=0, element_enchant = None, element_damage=0): #, protection=None, enchanted=None):
        
        self.max_hp_bonus = max_hp_bonus
        self.damage_bonus = damage_bonus
        self.armor_bonus = armor_bonus
        self.wit_bonus = wit_bonus
        self.strength_bonus = strength_bonus
        self.spirit_bonus = spirit_bonus
        
        self.element_enchant = element_enchant
        self.element_damage = element_damage
        
        self.slot = slot
        self.is_equipped = False

    def toggle_equip(self, user):  #toggle equip/dequip status
        if self.is_equipped:
            self.dequip(user)
        else:
            self.equip(user)

    def equip(self, owner):
        #if the slot is already being used, check for dual wield skill and/or dequip whatever is there first
        old_equipment = get_equipped_in_slot(self.slot, owner)
        if old_equipment is not None:
            
            old_equipment.dequip(owner)        

        #equip object and show a message about it
        self.is_equipped = True
        #message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', 'light green')

    def dequip(self, user):
        #dequip object and show a message about it
        if not self.is_equipped: return
        
        
        if self.owner.base_name == 'dagger':
            self.slot = 'right hand'
        
        self.is_equipped = False
        #message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)
        

def get_equipped_in_slot(slot, owner):  #returns the equipment in a slot, or None if it's empty
    for obj in owner.fighter.inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            return obj.equipment
    return None

def get_all_equipped(wearer):  #returns a list of equipped items someone wears
    equipped_list = []
    for item in wearer.fighter.inventory:
        if item.equipment and item.equipment.is_equipped:
            equipped_list.append(item.equipment)
    return equipped_list

    
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def make_map():
    global map, special_dict
    #general function for decision, which map to make
    #print direction,dungeon_level, 'DEBUG'
    
    #make the map
    map = []
    
    #map.append(make_floors('abyss'))
    
    for i in range(1):
        map.append(make_floors('abyss'))
    
    for i in range(1,5):
        map.append(make_abyss(i))
    
    for i in range(5,9):
        map.append(make_floors('air'))
    
    map.append(make_floors('rock wall'))
    map.append(make_floors('empty'))
    
    for i in range(11,14):
        map.append(make_floors('air'))
    
    for i in range(14,20):
        map.append(make_floors('rock wall'))
    
    map = unlevel_terrain(map, 'granite', 10)
    
    map = unlevel_terrain(map, 'air', 14)
    
    map.append(make_floors('empty'))
    
    for i in range(21,30):
        map.append(make_floors('air'))
    
    for i in range(30,50):
        map.append(make_floors('rock wall'))
    
    map.append(make_floors('empty'))
    
    for i in range(51, MAP_Z):
        map.append(make_floors('sky'))
        
    map = unlevel_terrain(map, 'air', 30)
    
    map = unlevel_terrain(map, 'rock', 50)
    
    map = adjust_sky_transparency(map)
    
    place_trees()    

    for i in range(5):
        make_clouds(70+i)
    
    make_clouds(76)
    
    make_cathedral()
    
    make_sewers(44)
    
    p1 = connection_points['behind the altar']
    p2 = connection_points['sewers start']
    
    try:
        connect( p2[0],p2[1],p2[2], p1[0], p1[1], p1[2], type = 'air' )
        parameters['connection sewers'] = 1
    except:
        print 'FAIL:',p1,p2
        parameters['connection sewers'] = 0
        
    map = unlevel_terrain(map, 'granite', 20)
    
    map = make_village(20, map)
    
    map = make_dungeon(35, map)
    
    p3 = connection_points['sewers end']
    p4 = connection_points['dungeon start']
    
    connect( p4[0],p4[1],p4[2], p3[0], p3[1], p3[2], type = 'air' )
    
    p5 = connection_points['dungeon end']
    
    #make_block(p5[0],p5[1],p5[2]-7,1,1,9, 'air')
    make_stairs(p5[0],p5[1],p5[2]-6,6, type = 'air')
    
    map = make_chasm(map, MAP_WIDTH/2, 0, MAP_WIDTH/2, MAP_HEIGHT, 15, width = 2, depth = 11, noise = 10)
    
    make_chasm_bridge(20)
    
    map = make_chasm(map, 0, MAP_HEIGHT/2, MAP_WIDTH, MAP_HEIGHT/2, 10, width = 2, depth = 1, noise = 4, type = 'lava')
    map = make_chasm(map, MAP_WIDTH/2, 0, MAP_WIDTH/2, MAP_HEIGHT, 10, width = 2, depth = 1, noise = 10, type = 'lava' )
    
    #make_stone_slabs(10)
    
    make_block(40,18,8,5,1,7, 'air')
    make_block(42,17,8,1,5,7, 'air')
    
    make_castle(81)
    
    map = adjust_sky_transparency(map)
    
def make_stone_slabs(z):
    
    n = 0
    
    while True:
        x = libtcod.random_get_int(0,0,MAP_WIDTH-1)
        y = libtcod.random_get_int(0,0,MAP_HEIGHT-1)
        if map[z][x][y].type == 'lava':
            map[z][x][y].change_type('stone slab')
            ai = StoneSlab(ticker, 6, x,y,z)
            n += 1
        if n == 10:
            break
    
def make_abyss(n):
    #fill map with ground tiles for floor 0
    temp = [[ tiles.Tile(True, type = 'abyss')
             for y in range(MAP_HEIGHT) ]
           for x in range(MAP_WIDTH) ]
    
    for row in temp:
        for tile in row:
            if libtcod.random_get_int(0,0,100) < 20*n:
                tile.change_type('air')
    
    return temp
    
def make_floors(type):
     #fill map with ground tiles for floor 0
    temp = [[ tiles.Tile(True, type = type)
             for y in range(MAP_HEIGHT) ]
           for x in range(MAP_WIDTH) ]
    return temp
    
def surrounded_by(type, x, y, z):
    for n in range(-1,2):
        for m in range(-1,2):
            if map[z][x+n][y+m].type == type:
                return True
                
    return False
    
def make_castle(z):
    
    x = libtcod.random_get_int(0,3,6) #3
    y = libtcod.random_get_int(0,3,6) #3
    z = z
    
    l = libtcod.random_get_int(0,30,32) #30
    w = libtcod.random_get_int(0,14,16) #15
    h = 5
    
    parameters['castle coordinates'] = (x-2,x+l+1, y-2,y+w+1,z,z+20)
    
    #base block
    make_block(x,y, z, l, w, h, 'rock wall' )
    
    #carve out wall
    make_block(x+1,y+1, z+1, l-2, w-2, h-2, 'sky' )
    #carve out opening
    make_block(x+2,y+2, z+h-1, l-4, w-4, 2, 'sky' )
    
    #make stairs to rail
    a = libtcod.random_get_int(0,5,10)
    connect(x+l-h-a, y+w-2, z, x+l-a, y+w-2, z+h)
    
    #tower1
    m = libtcod.random_get_int(0,0,3)
    n = libtcod.random_get_int(0,0,3)
    o = libtcod.random_get_int(0,0,5)
    make_block(x-1, y-1, z+1, 4+m, 4+n, 7+o, 'rock wall' )
    #tower rail entrance
    make_block(x+1, y+1, z+h, 1, 3+n, 1, 'sky' )
    make_block(x+1, y+1, z+h, 3+m, 1, 1, 'sky' )
    #hollow tower
    make_block(x, y, z+1, 4+m-2, 4+n-2, 7+o-1, 'sky' )
    #apart from the midheight entrance
    make_block(x, y, z+h-1, 4+m-1, 4+n-2, 1, 'rock wall' )
    #make top
    make_block(x-2, y-2, z+7+o, 4+m+2, 4+n+2, 2, 'rock wall' )
    make_block(x-1, y-1, z+7+o+1, 4+m, 4+n, 1, 'sky' )
    make_block(x, y-2, z+7+o+1, 1, 4+n+3, 1, 'sky' )
    make_block(x-2, y, z+7+o+1, 4+m+3, 1, 1, 'sky' )
    make_block(x+m+1, y-2, z+7+o+1, 1, 4+n+3, 1, 'sky' )
    make_block(x-2, y+n+1, z+7+o+1, 4+m+3, 1, 1, 'sky' )
    #make stairs
    make_stairs(x,y,z+1,7+o)
    
    #tower2
    m = libtcod.random_get_int(0,0,3)
    n = libtcod.random_get_int(0,0,3)
    o = libtcod.random_get_int(0,0,5)
    p = w-n-2
    make_block(x-1, y+p-1, z+1, 4+m, 4+n, 7+o, 'rock wall' )
    #tower rail entrance
    make_block(x+1, y+p-1, z+h, 1, 3+n, 1, 'sky' )
    make_block(x+1, y+p+n, z+h, 3+m, 1, 1, 'sky' )
    #hollow tower
    make_block(x, y+p, z+1, 4+m-2, 4+n-2, 7+o-1, 'sky' )
    #apart from the midheight entrance
    make_block(x, y+p, z+h-1, 4+m-1, 4+n-2, 1, 'rock wall' )
    #make top
    make_block(x-2, y+p-2, z+7+o, 4+m+2, 4+n+2, 2, 'rock wall' )
    make_block(x-1, y+p-1, z+7+o+1, 4+m, 4+n, 1, 'sky' )
    make_block(x, y+p-2, z+7+o+1, 1, 4+n+2, 1, 'sky' )
    make_block(x-2, y+p, z+7+o+1, 4+m+3, 1, 1, 'sky' )
    make_block(x+m+1, y+p-2, z+7+o+1, 1, 4+n+2, 1, 'sky' )
    make_block(x-2, y+p+n+1, z+7+o+1, 4+m+3, 1, 1, 'sky' )
    #make stairs
    make_stairs(x,y+p,z+1,7+o)
    
    
    #tower3
    m = libtcod.random_get_int(0,0,3)
    n = libtcod.random_get_int(0,0,3)
    o = libtcod.random_get_int(0,0,5)
    p = w-n-2
    q = l-m-2
    make_block(x+q-1, y+p-1, z+1, 4+m, 4+n, 7+o, 'rock wall' )
    #tower rail entrance
    make_block(x+q+m, y+p-1, z+h, 1, 3+n, 1, 'sky' )
    make_block(x+q-1, y+p+n, z+h, 3+m, 1, 1, 'sky' )
    #hollow tower
    make_block(x+q, y+p, z+1, 4+m-2, 4+n-2, 7+o-1, 'sky' )
    #apart from the midheight entrance
    make_block(x+q, y+p, z+h-1, 4+m-1, 4+n-2, 1, 'rock wall' )
    #make top
    make_block(x+q-2, y+p-2, z+7+o, 4+m+2, 4+n+2, 2, 'rock wall' )
    make_block(x+q-1, y+p-1, z+7+o+1, 4+m, 4+n, 1, 'sky' )
    make_block(x+q, y+p-2, z+7+o+1, 1, 4+n+2, 1, 'sky' )
    make_block(x+q-2, y+p, z+7+o+1, 4+m+3, 1, 1, 'sky' )
    make_block(x+q+m+1, y+p-2, z+7+o+1, 1, 4+n+2, 1, 'sky' )
    make_block(x+q-2, y+p+n+1, z+7+o+1, 4+m+3, 1, 1, 'sky' )
    #make stairs
    make_stairs(x+q,y+p,z+1,7+o)
    
    #main facilities
    m = libtcod.random_get_int(0,12,16)
    n = libtcod.random_get_int(0,6,9)
    o = libtcod.random_get_int(0,5,8)
    make_house(x+l-m,y,z+1,m,n,o)
    map[z+o][x+l-m/2][y+n/2].change_type('throne')
    parameters['throne'] = (x+l-m/2,y+n/2,z+o)
    
    #ground entrances
    make_block(x+1,y+1, z+1, 1, w-2, 1, 'sky' )
    make_block(x+1,y+1, z+1, l-2, 1, 1, 'sky' )
    make_block(x+1,y+w-2, z+1, l-2, 1, 1, 'sky' )
    make_block(x+l-2,y+1, z+1, 1, w-2, 1, 'sky' )
    
    #make_bridge and entrance
    make_bridge(x+l,y+w/2+2,z+1,7)
    
    #make well
    make_block(x+7,y+7, z+1, 3, 3, 1, 'rock wall' )
    make_block(x+6,y+6, z-4, 5, 5, 4, 'rock wall' )
    make_block(x+8,y+8, z-2, 1, 1, 5, 'water' )
    make_block(x+7,y+7, z-3, 3, 3, 1, 'water' )
    make_block(x+7,y+7, z-4, 3, 3, 1, 'empty' )
    
def make_sewers(z):
    
    #grid of channels with water
    
    #number of vertical/horizontal lines
    v = libtcod.random_get_int(0,3,5)
    h = libtcod.random_get_int(0,3,5)
    
    #start and end points for exit
    exit = []
    
    #make the lines empty
    for n in range(v):
        make_block( n*(MAP_WIDTH/v)+3, 1, z, 1,MAP_HEIGHT-2, 2, 'air' )
        if n == 2:
            connection_points['sewers start'] = (n*(MAP_WIDTH/v)+3, 1, z+1)
            
        for k in range(MAP_HEIGHT-2):
            if libtcod.random_get_int(0,0,100) < 25 and not surrounded_by('water',n*(MAP_WIDTH/v)+3 , k, z):
                map[z][n*(MAP_WIDTH/v)+3][k].change_type('water')
                #map[z-1][n*(MAP_WIDTH/v)+3][k].change_type('empty')
            
        exit.append( (n*(MAP_WIDTH/v)+3, 1) )
        exit.append( (n*(MAP_WIDTH/v)+3, MAP_HEIGHT-2) )
        
    for m in range(h):
        make_block( 1, m*(MAP_HEIGHT/h)+3, z, MAP_WIDTH-2,1, 2, 'air' )
        for l in range(MAP_WIDTH-2):
            if libtcod.random_get_int(0,0,100) < 25 and not surrounded_by('water', l, m*(MAP_HEIGHT/h)+3, z):
                map[z][l][m*(MAP_HEIGHT/h)+3].change_type('water')
                #map[z-1][l][m*(MAP_HEIGHT/h)+3].change_type('empty')
            
        exit.append( (1, m*(MAP_HEIGHT/h)+3) )
        exit.append( (MAP_WIDTH-2, m*(MAP_HEIGHT/h)+3) )
        
    for x in range(MAP_WIDTH):
        for y in range(MAP_HEIGHT):
            if map[z][x][y].type == 'water':
                map[z-1][x][y].change_type('empty')
    
    #make exit
    random.shuffle(exit)
    make_block(exit[0][0], exit[0][1], z-2, 1,1, 3, 'air')
    connection_points['sewers end'] = (exit[0][0],exit[0][1],z-2  )
    
    
        
def connect(x,y,z,x2,y2,z2, type='sky'):
    
    dz = z2 - z
    dx = x2 - x
    dy = y2 - y
    r = z2

    #always reachable
    if abs(dz) > abs(dx) + abs(dy):
        z2 = z + abs(dx) + abs(dy) 
        dz = z2 - z
    
    #adjust slope ratio for x path and y path
    
    d = float(abs(dx)) / (abs(dx) + float(abs(dy)))
    i = z + dz * d
    
    i = int(i)
    
    #first x    
    libtcod.line_init(x, z, x2, i)
    while True:
        (a, b) = libtcod.line_step()
        if not a:
            break
        map[b][a][y].change_type('empty')
        map[b+1][a][y].change_type(type)
        
    #then y
    libtcod.line_init(y, i, y2, z2)
    while True:
        (a, b) = libtcod.line_step()
        if not a:
            break
        map[b][x2][a].change_type('empty')
        map[b+1][x2][a].change_type(type)
        
    if r != z2:
        if r > z2:
            make_stairs(x2,y2,z2,r-z2)
        else:
            make_stairs(x2,y2,z2,z2-r)
                
def make_cathedral():
    
    #find the rectangle on the ground to build cathedral
    #x = 0
    #y = 0
    z = 50
    
    for x in range(4,MAP_WIDTH-7):
        for y in range(2,MAP_HEIGHT-7):
            a = 0
            b = 0
            for a in range(7):
                if map[z][x+a][y+b].type != 'empty':
                        break
                for b in range(7):
                    if map[z][x+a][y+b].type != 'empty':
                        break
                    if a == 6 and b == 6:
                        make_block(x+a/2,y,50, 4,4,15, 'rock wall')
                        make_block(x,y,50, a,b,10, 'rock wall')                        
                        make_block(x+1,y+1,50, a-2,b-2,9, 'air')
                        make_block(x+a/2+1,y+1,50, 2,2,14, 'air')
                        make_stairs(x+a/2+1,y+1, 50, 15)
                        
                        parameters['church coordinates'] = (x-1,x+a+1,y-1,y+b,47,66)
                        
                        #altar & door                        
                        objects[50].append(create_object('altar', x+a/2-1, y+b-3))
                        if not map[50][x+a/2-1][y-1].blocked:
                            map[50][x+a/2-1][y].change_type('door')
                        elif not map[50][x-1][y+b/2-1].blocked:
                            map[50][x][y+b/2-1].change_type('door')
                        elif not map[50][x+a][y+b/2+1].blocked:
                            map[50][x+a-1][y+b/2+1].change_type('door')
                        
                        
                        #way down
                        make_block(x+a/2-1, y+b-2, 47, 1,1, 3, 'air')
                        #make_block(x+a/2-1, y+b-2-5, 45, 1,8, 1, 'air')
                        
                        #parameter
                        connection_points['behind the altar'] = (x+a/2-1, y+b-2, 47)
                        
                        parameters['church'] = 1
                        
                        return
    
    #select starting point from ground floor 
    
def make_house(x,y,z,l,w,h):
    
    make_block(x,y,z,l,w,h, 'rock wall')
    make_block(x+1,y+1,z,l-2,w-2,h, 'empty')
    make_stairs(x+1,y+1,z,h)
    
    # if not map[z][x+l/2][y-1].blocked:
        # map[z][x+l/2][y].change_type('empty')
    # elif not map[z][x-1][y+w/2].blocked:
        # map[z][x][y+w/2].change_type('empty')
    # elif not map[z][x+l][y+w/2+1].blocked:
        # map[z][x+l][y+w/2].change_type('empty')
    
    
def make_chasm(map, start_x, start_y, end_x, end_y, z, width = 5, depth = 1, noise = 100, type= 'air'):
    
    dir = 'h'
    end_x += 10 #correction to cut off noise at the end BUG?
    if end_y - start_y > end_x - start_x:
        dir = 'v'
        end_y += 10 #correction to cut off noise at the end BUG?
    
    #start parameters
    points = [
    (start_x, start_y), 
    ( int(end_x - start_x / 2), int(end_y - start_y / 2) ), 
    (end_x, end_y)
    ]
    max_disp = noise
    scale = 0.5
    
    #iterations
    for i in range(0,9):
        points = displace(points, max_disp, dir)
        max_disp = int(max_disp * scale)
    
    for p in points:
        map = dig_square(map, z, depth, p, width, type)
        
    return map

def displace(points, max_disp, dir):
    
    last_point = points[0]
    new_points = [last_point]
    
    for next_point in points[1:]:
        midpoint_x = int( 0.5 * ( last_point[0] + next_point[0] ) )
        midpoint_y = int( 0.5 * ( last_point[1] + next_point[1] ) )
        
        #displace according to direction
        if dir == 'h':
            midpoint_y += libtcod.random_get_int(0, max_disp*-1, max_disp)
        else:
            midpoint_x += libtcod.random_get_int(0, max_disp*-1, max_disp)
        
        new_points.append( (midpoint_x, midpoint_y) )
        new_points.append( next_point )
        
        last_point = next_point
    
    return new_points

def dig_square(map, z, depth, point, dimension, type):
    
    for x in range(-dimension, dimension):
        for y in range(-dimension, dimension):
            try:
                for d in range(depth):
                    map[z+d][point[0]+x][point[1]+y].change_type(type)
            except:
                pass
    return map
        
def place_trees():
    z = 54 #highest level of grass
    
    temp = map[z]
    points = []

    for xa in range(3,MAP_WIDTH-3):
        for ya in range(3,MAP_HEIGHT-3):
            if temp[xa][ya].type == 'grass' and temp[xa+1][ya].type == 'grass' and temp[xa][ya+1].type == 'grass' and temp[xa+1][ya+1].type == 'grass':
                #set point
                points.append((xa,ya))
                #delete neighbor spots
                for a in range(-3,4):
                    for b in range(-3,4):
                        temp[xa+a][ya+b].change_type('sky')
                

    for n in range(3):
        if points:
            p = libtcod.random_get_int(0,0,len(points)-1)
            
            point = points[p]
            
            del points[p]
            
            h = 15#libtcod.random_get_int(0,10,15)
            
            for i in range(h):
                for j in range(MAP_WIDTH):
                    for k in range(MAP_HEIGHT):
                        if distance_2_point(j,k,point[0],point[1]) < 2.5 and libtcod.random_get_int(0,0,100) < 50:
                            map[z+i+1][j][k].change_type('leaf')
                    
                # if i == h-1:
                    # connect(point[0],point[1], z+h, point[0]+10,point[1]+10,z+h+25, 'empty' )
                    # #make_stairs(point[0],point[1], z + h, 20)
                            
            make_block(point[0],point[1],z, 1,1, h-2, 'tree'  )
            
            #check parameters for world
            #tree_height = 54 + h
            parameters['number of trees'] += 1
                
def make_clouds(z):
    #return
    #for t in range(5): #floors
    for u in range(5): #cloud_y distribution
        for o in range(2): #two per row            
            point_c = libtcod.random_get_int(0,0,MAP_WIDTH), u*5 
            for q in range(MAP_WIDTH):
                for w in range(MAP_HEIGHT):
                    if distance_2_point(q,w,point_c[0],point_c[1]) < 5 and libtcod.random_get_int(0,0,100) < 90:
                        objects[z].append(create_object('cloud', q , w ))

def make_stairs( x, y, z, h,type = 'sky'):
        i = 1
        for j in range(h):
            map[z+j][x+i][y].change_type('empty')
            map[z+j+1][x+i][y].change_type(type)
            if i == 1: i = 0
            else: i = 1
    
def unlevel_terrain(map, type, floor):
    global ground_floor
    ground_floor = []

    #make heightmap and put it on map
    test = libtcod.heightmap_new(MAP_WIDTH, MAP_HEIGHT)
    test2 = libtcod.heightmap_new(MAP_WIDTH, MAP_HEIGHT)
    test3 = libtcod.heightmap_new(MAP_WIDTH, MAP_HEIGHT)
    
    noise = libtcod.noise_new(2)
    
    libtcod.heightmap_add_fbm(test2, noise, 1, 1, 0.0, 0.0, 10, 0.0, 1.0)
    libtcod.heightmap_add_fbm(test3, noise, 2, 2, 0.0, 0.0,  5, 0.0, 1.0)
    
    libtcod.heightmap_multiply_hm(test2, test3, test)
    libtcod.heightmap_normalize(test, mi=0, ma=1)
    
    for x in range(MAP_WIDTH):
        for y in range(MAP_HEIGHT):
            if libtcod.heightmap_get_value(test, x, y) < 0.2:
                libtcod.heightmap_set_value(test, x, y, 0)
                
                ground_floor.append((x,y))
                
            elif libtcod.heightmap_get_value(test, x, y) >= 0.2 and libtcod.heightmap_get_value(test, x, y) < 0.4:
                libtcod.heightmap_set_value(test, x, y, 1)
            elif libtcod.heightmap_get_value(test, x, y) >= 0.4 and libtcod.heightmap_get_value(test, x, y) < 0.6:
                libtcod.heightmap_set_value(test, x, y, 2)
            elif libtcod.heightmap_get_value(test, x, y) >= 0.6 and libtcod.heightmap_get_value(test, x, y) < 0.8:
                libtcod.heightmap_set_value(test, x, y, 3)
            elif libtcod.heightmap_get_value(test, x, y) >= 0.8:
                libtcod.heightmap_set_value(test, x, y, 4)
            
            # if libtcod.heightmap_get_value(test, x, y) < 0.1:
                # libtcod.heightmap_set_value(test, x, y, 0)
            # elif libtcod.heightmap_get_value(test, x, y) >= 0.1 and libtcod.heightmap_get_value(test, x, y) < 0.2:
                # libtcod.heightmap_set_value(test, x, y, 1)
            # elif libtcod.heightmap_get_value(test, x, y) >= 0.2 and libtcod.heightmap_get_value(test, x, y) < 0.3:
                # libtcod.heightmap_set_value(test, x, y, 2)
            # elif libtcod.heightmap_get_value(test, x, y) >= 0.3 and libtcod.heightmap_get_value(test, x, y) < 0.4:
                # libtcod.heightmap_set_value(test, x, y, 3)
            # elif libtcod.heightmap_get_value(test, x, y) >= 0.4 and libtcod.heightmap_get_value(test, x, y) < 0.5:
                # libtcod.heightmap_set_value(test, x, y, 4)
            # elif libtcod.heightmap_get_value(test, x, y) >= 0.5 and libtcod.heightmap_get_value(test, x, y) < 0.6:
                # libtcod.heightmap_set_value(test, x, y, 5)
            # elif libtcod.heightmap_get_value(test, x, y) >= 0.6 and libtcod.heightmap_get_value(test, x, y) < 0.7:
                # libtcod.heightmap_set_value(test, x, y, 6)
            # elif libtcod.heightmap_get_value(test, x, y) >= 0.7 and libtcod.heightmap_get_value(test, x, y) < 0.8:
                # libtcod.heightmap_set_value(test, x, y, 7)
            # elif libtcod.heightmap_get_value(test, x, y) >= 0.8 and libtcod.heightmap_get_value(test, x, y) < 0.9:
                # libtcod.heightmap_set_value(test, x, y, 8)
            # elif libtcod.heightmap_get_value(test, x, y) >= 0.9:
                # libtcod.heightmap_set_value(test, x, y, 9)
    
    for x in range(MAP_WIDTH):
        for y in range(MAP_HEIGHT):
            for z in range(int(int(libtcod.heightmap_get_value(test, x, y)))):#-1)):
                map[z+floor][x][y].change_type(type)
    
    libtcod.heightmap_delete(test)
    return map
    
def adjust_sky_transparency(map):
    # changes the sky tiles, if something is directly below
    for z in range(1, MAP_Z):
        for x in range(MAP_WIDTH):
            for y in range(MAP_HEIGHT):
                #print x,y,z
                if map[z][x][y].type == 'sky' and map[z-1][x][y].type == 'rock wall':
                    map[z][x][y].change_type('empty')
                elif map[z][x][y].type == 'sky' and map[z-1][x][y].type == 'rock':
                    map[z][x][y].change_type('grass')
                elif map[z][x][y].type == 'sky' and map[z-1][x][y].type == 'tree':
                    map[z][x][y].change_type('grass')

                elif map[z][x][y].type == 'air' and map[z-1][x][y].type == 'rock wall':
                    map[z][x][y].change_type('empty')
                
                elif map[z][x][y].type == 'air' and map[z-1][x][y].type == 'granite':
                    map[z][x][y].change_type('rubble')
                
                elif map[z][x][y].type == 'air' and map[z-1][x][y].type == 'rock':
                    map[z][x][y].change_type('grass')
                
                if map[z][x][y].type == 'sky' and not map[z-1][x][y].type == 'sky':
                    #color_mix = libtcod.color_lerp(map[z-1][x][y].color_light, libtcod.sky, 0)
                    #color = str(T.color_from_argb(0, color_mix[0], color_mix[1], color_mix[2]))
                    map[z][x][y].color_light = map[z-1][x][y].color_light
                    map[z][x][y].char_light = '-'
        
                    if map[z+1][x][y].type == 'sky':
                        #color_mix = libtcod.color_lerp ( map[z-1][x][y].color_light, libtcod.sky, 0.4)
                        #color = str(T.color_from_argb(0, color_mix[0], color_mix[1], color_mix[2]))
                        map[z+1][x][y].color_light = map[z-1][x][y].color_light
                        map[z+1][x][y].char_light = '='
                        
                if map[z][x][y].type == 'air' and not map[z-1][x][y].type == 'air':
                    #color_mix = libtcod.color_lerp(map[z-1][x][y].color_light, libtcod.sky, 0)
                    #color = str(T.color_from_argb(0, color_mix[0], color_mix[1], color_mix[2]))
                    map[z][x][y].color_light = map[z-1][x][y].color_light
                    map[z][x][y].char_light = '-'
        
                    if map[z+1][x][y].type == 'air':
                        #color_mix = libtcod.color_lerp ( map[z-1][x][y].color_light, libtcod.sky, 0.4)
                        #color = str(T.color_from_argb(0, color_mix[0], color_mix[1], color_mix[2]))
                        map[z+1][x][y].color_light = map[z-1][x][y].color_light
                        map[z+1][x][y].char_light = '='
                    
    # for z in range(1, MAP_Z):
        # for x in range(MAP_WIDTH):
            # for y in range(MAP_HEIGHT):
                # if map[z][x][y].type == 'sky' and not map[z-1][x][y].type == 'sky':
                    # #color_mix = libtcod.color_lerp(map[z-1][x][y].color_light, libtcod.sky, 0)
                    # #color = str(T.color_from_argb(0, color_mix[0], color_mix[1], color_mix[2]))
                    # map[z][x][y].color_light = map[z-1][x][y].color_light
                    # map[z][x][y].char_light = '-'
        
                    # if map[z+1][x][y].type == 'sky':
                        # #color_mix = libtcod.color_lerp ( map[z-1][x][y].color_light, libtcod.sky, 0.4)
                        # #color = str(T.color_from_argb(0, color_mix[0], color_mix[1], color_mix[2]))
                        # map[z+1][x][y].color_light = map[z-1][x][y].color_light
                        # map[z+1][x][y].char_light = '='
                        
    return map       
 
def make_block(x,y,z, l,w,h, type):
    #x,y,z is the lower top left corner of the block
    
    for a in range(h):
        for b in range(l):
            for c in range(w):
                map[z+a][x+b][y+c].change_type(type)

                
def is_blocked(x, y, z):
    try:
        #first test the map tile
        if map[z][x][y].blocked:
            return True
        #now check for any blocking objects
        for object in objects[z]:
            if object.blocks and object.x == x and object.y == y:
                return True
    except: # most of the times things outside the map
        return True
    
    return False
    
def create_room(room, z, h, map):
    
    temp = map
    
    for i in range(h):
        
        #go through the tiles in the rectangle and make them passable
        for x in range(room.x1 + 1, room.x2):
            for y in range(room.y1 + 1, room.y2):
                if i == 0:
                    temp[z+i][x][y].change_type('empty')
                else:
                    temp[z+i][x][y].change_type('air')
        #create the outter walls
        for x in range(room.x1, room.x2+1):
            if temp[z+i][x][room.y1].type == 'rock wall':
                temp[z+i][x][room.y1].change_type('horizontal wall')
                
            if temp[z+i][x][room.y2].type == 'rock wall':
                temp[z+i][x][room.y2].change_type('horizontal wall')
                
        for y in range(room.y1, room.y2+1):
            if temp[z+i][room.x1][y].type == 'rock wall':
                temp[z+i][room.x1][y].change_type('vertical wall')
                
            if temp[z+i][room.x2][y].type == 'rock wall':
                temp[z+i][room.x2][y].change_type('vertical wall')
                
    return temp
                      
def create_h_tunnel(x1, x2, y, z, map):
    #horizontal tunnel. min() and max() are used in case x1>x2
    for x in range(min(x1, x2), max(x1, x2) + 1):
        if map[z][x][y]. type != 'air':
            map[z][x][y].change_type('empty')
    return map
        
def create_v_tunnel(y1, y2, x, z, map): 
    #vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        if map[z][x][y]. type != 'air':
            map[z][x][y].change_type('empty')
    return map
  
def make_dungeon(z, map):
    
    temp = map
    
    rooms = []
    num_rooms = 0

    for r in range(MAX_ROOMS):
        #random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)

        #run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed: #THIS??????
        
            #this means there are no intersections, so this room is valid

            #"paint" it to the map's tiles
            temp = create_room(new_room, z, 3, temp)
            
            #add some contents to this room, such as monsters or special rooms
            
            #place_objects(z, new_room)
                
            #center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                 connection_points['dungeon start'] = ( new_x, new_y, z+2   )
                
            else:
                #all rooms after the first:
                #connect it to the previous room with a tunnel

                #center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms-1].center()

                #vary height by 1 or not
                i = libtcod.random_get_int(0,0,1)
                    
                #draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                      
                    #first move horizontally, then vertically
                    temp = create_h_tunnel(prev_x, new_x, prev_y, z+i, temp)
                    temp = create_v_tunnel(prev_y, new_y, new_x, z+i, temp)
                else:
                    #first move vertically, then horizontally
                    temp = create_v_tunnel(prev_y, new_y, prev_x, z+i, temp)
                    temp = create_h_tunnel(prev_x, new_x, new_y, z+i, temp)

            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1
        
        else:
            pass
    
    #obstacles
    for room in rooms:
            
        if libtcod.random_get_int(0,0,1) == 0:
            for x in range(room.x1+1, room.x2):
                temp[z][x][room.y1+2].change_type('rock wall')
            
        else:    
            for y in range(room.y1+1, room.y2):
                temp[z][room.x1+2][y].change_type('rock wall')
            
    connection_points['dungeon end'] = ( new_x, new_y, z )
    
    del rooms[0]
    del rooms[-1]
    random.shuffle(rooms)
    
    while True:
        a = libtcod.random_get_int(0,1,rooms[0].x2-1)
        b = libtcod.random_get_int(0,1,rooms[0].y2-1)
        if not is_blocked(a,b,z) and map[z][a][b].type == 'empty':
            break
        
    objects[z].append(create_item('hunting_glasses',a,b,z))
    return temp
    
def make_bridge(x,y,z,length):
    
    for l in range(-1,length+1):
        
        map[z][x+l][y-1].change_type('bridge')
        map[z][x+l][y].change_type('bridge')
        
        if l == -1 or l == length:
            map[z][x+l][y-2].change_type('pillar')
            map[z][x+l][y+1].change_type('pillar')
        else:
            map[z][x+l][y-2].change_type('ropes')
            map[z][x+l][y+1].change_type('ropes')
        
    #hole
    map[z][x+length/2][y].change_type('air')
    
    
def make_chasm_bridge(z):
    
    y_start = libtcod.random_get_int(0,3,MAP_HEIGHT-3)
    x1 = 0
    length = 0
    
    for x in range(MAP_WIDTH):
        if map[z][x][y_start].type == 'air' and not x1:
            x1 = x
        if map[z][x][y_start].type == 'air':
            length += 1
            
    make_bridge(x1,y_start,z,length)
        
def make_village(z, map):    
    temp = map
    rooms = []
    num_rooms = 0

    for r in range(MAX_ROOMS):
        #random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)

        #run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed: #THIS??????
        
            #this means there are no intersections, so this room is valid

            #"paint" it to the map's tiles
            z2 = libtcod.random_get_int(0,2,5)
            make_house(new_room.x1, new_room.y1, z, new_room.w, new_room.h, z2)
            
            #add some contents to this room, such as monsters or special rooms
            
            #place_objects(z, new_room)
                
            #center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                 pass
                
            else:
                #all rooms after the first:
                #connect it to the previous room with a tunnel

                #center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms-1].center()

                #draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                      
                    #first move horizontally, then vertically
                    temp = create_h_tunnel(prev_x, new_x, prev_y, z, temp)
                    temp = create_v_tunnel(prev_y, new_y, new_x, z, temp)
                else:
                    #first move vertically, then horizontally
                    temp = create_v_tunnel(prev_y, new_y, prev_x, z, temp)
                    temp = create_h_tunnel(prev_x, new_x, new_y, z, temp)

            
            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1
        
        else:
            pass
    
    parameters['rooms'] = rooms
    
    return temp
    
    
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def create_monster(type, x, y, z):
    # storage of data from monsters.py
    a = getattr(monsters, type)
    
    hp = 1
    wit = 0
    str = 0
    
    #randomly distribute stat points to three attributes
    for i in range(a['stat_points']):
        r = libtcod.random_get_int(0,0,100)
        if r <= 33:
            hp += 1
        elif r <= 66:
            wit += 1
        else:
            str += 1
    
    # creating fighter component
    fighter_component = Fighter(hp=hp, damage=0, armor=0, wit=wit, strength=str, spirit=a['spirit'], speed=a['speed'], xp=a['xp'], death_function=DEATH_DICT[a['death_function']])                
    
    #creating ai needs more info because of arguments
    if a['ai'] == 'AIkobold':
        ai_component = AIkobold(ticker, speed=a['speed'])
    elif a['ai'] == 'AIgoblin':
        ai_component = AIgoblin(ticker, speed=a['speed'])
    elif a['ai'] == 'AIorc':
            ai_component = AIorc(ticker, speed=a['speed'])
    elif a['ai'] == 'AIhuman':
            ai_component = AIhuman(ticker, speed=a['speed'])
    elif a['ai'] == 'AIelf':
            ai_component = AIelf(ticker, speed=a['speed'])
    elif a['ai'] == 'AINPC':
            ai_component = AINPC(ticker, speed=a['speed'])

            
    if 'skills' in a:
        skills_m = ['armor wearer', 'double dagger', 'elementalist', 'spell slinger', 'range ranger']
        random.shuffle(skills_m)
        for i in range(a['skills']):
            if libtcod.random_get_int(0,0,100) < 50:
                fighter_component.skills.append(skills_m.pop())
        
    #create the monster    
    monster = Object(x, y, z, a['char'], a['name'], a['color'], blocks=True, fighter=fighter_component, ai=ai_component)
    
    if 'inventory' in a:
        for item in a['inventory']:
            if libtcod.random_get_int(0,0,100) < item[1]:
                if item[0] == 'potion':
                    list = ['potion_of_healing', 'potion_of_berserk_rage', 'potion_of_magma', 'potion_of_tangerine_juice', 'potion_of_invisibility']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                elif item[0] == 'scroll':
                    list = ['scroll_of_light', 'scroll_of_teleport', 'scroll_of_enchantment']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                elif item[0] == 'wand':
                    list = ['wand_of_digging', 'wand_of_air', 'wand_of_fireball', 'wand_of_waterjet']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                elif item[0] == 'ring':
                    list = ['ring_of_fire_resistance', 'ring_of_invisibility', 'hunger_ring', 'lucky_ring', 'ring_of_strength']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                    i.equipment.equip(monster)
                elif item[0] == 'glasses':
                    list = ['lenses_of_see_invisible', 'sunglasses_of_elemental_protection', 'nerd_glasses', 'glasses_of_telepathy', 'Xray_visor']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                    i.equipment.equip(monster)
                elif item[0] == 'spellbook':
                    list = ['book_of_sunfire', 'book_of_waterjet', 'book_of_weakness']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                    i.equipment.equip(monster)
                else:
                    i = create_item(item[0], z = z)
                    monster.fighter.inventory.append(i)
                    if i.equipment:
                        i.equipment.equip(monster)
                            
    return monster
                
def create_item(type, x=0, y=0, z=0): 
    a = getattr(items, type)
    
    if 'equipment' in a:
        equipment_component = Equipment(slot=a['slot'])
        
        for value in a:
            if 'bonus' in value:
                setattr(equipment_component, value, a[value])
    
    else:
        equipment_component = None

    item_component = Item()
    
    if 'stackable' in a:
        item_component.stackable = True
    
    if 'use_function' in a:
        item_component.use_function = globals()[a['use_function']]
    
    if 'spell_function' in a:
        item_component.spell_function = globals()[a['spell_function']]
     
    if 'charges' in a:
        item_component.charges = libtcod.random_get_int(0,1,5)
        item_component.max_charges = item_component.charges
    
    item = Object(x, y, z, a['char'], a['name'], a['color'], item=item_component, equipment=equipment_component)
    
    return item

def create_object(type, x=0, y=0, z=0):
    a = getattr(items, type)
    
    obj = Object(x, y, z, a['char'], a['name'], a['color'] )
    
    if 'blocks' in a:
        obj.blocks = a['blocks']
    
    if a['name'] == 'cloud':
        temp = CloudTicker(ticker, speed=12)
        temp.owner = obj
    
    return obj
    
            
class CloudTicker:
    '''checking altar for sacrifices'''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
    def take_turn(self):
        cloud = self.owner
        
        if cloud.x < MAP_WIDTH:
            cloud.x += 1
        else:
            cloud.x = 0
        
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      

        
class StoneSlab:
    def __init__(self, ticker, speed,x,y,z):
        self.ticker = ticker
        self.speed = speed
        self.x = x
        self.y = y
        self.z = z
        self.ticker.schedule_turn(self.speed, self)
        
        self.directions = [(0,-1), (-1,0), (0,1), (1,0)]
        self.curr_dir = 0
        
    def take_turn(self):
        
        map[self.z][self.x][self.y].change_type('lava')
        n = 0
        while True:
            n += 1
            a = self.directions[self.curr_dir][0]
            b = self.directions[self.curr_dir][1]
            
            if self.x+a >= MAP_WIDTH or self.y+b >= MAP_HEIGHT or self.x+a < 0 or self.y+b < 0:
                self.change_dir()
                if n == 30:
                    break
            elif map[self.z][self.x+a][self.y+b].type != 'lava':
                self.change_dir()
                if n == 30:
                    break
            else:
                self.x = self.x+a
                self.y = self.y+b
                break
        
        map[self.z][self.x][self.y].change_type('stone slab')
        
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      

    def change_dir(self):
        self.curr_dir += 1
        if self.curr_dir >= 4:
            self.curr_dir = 0
    
def generate_name(length=5):
    
    cons = ['b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z']
    voc = ['a', 'e', 'i', 'o', 'u']
    name = []
    
    for i in range(length):
        if i%2==0:
            name.append(cons[libtcod.random_get_int(0,0,len(cons)-1)])
        else:    
            name.append(voc[libtcod.random_get_int(0,0,len(voc)-1)])
            
    return ''.join(name)
        
    
def random_choice_index(chances):  #choose one option from list of chances, returning its index
    #the dice will land on some number between 1 and the sum of the chances
    dice = libtcod.random_get_int(0, 1, sum(chances))

    #go through all chances, keeping the sum so far
    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w

        #see if the dice landed in the part that corresponds to this choice
        if dice <= running_sum:
            return choice
        choice += 1

def random_choice(chances_dict):
    #choose one option from dictionary of chances, returning its key
    chances = chances_dict.values()
    strings = chances_dict.keys()

    return strings[random_choice_index(chances)]

def from_dungeon_level(z, table):
    #returns a value that depends on level. the table specifies what value occurs after each level, default is 0.
    for (value, level) in reversed(table):
        if z >= level:
            return value
    return 0

def place_objects(z, room):
    global SUM, RIN, POT, SCR, ARM, WEA, BOO, WAN, GLA
    #this is where we decide the chance of each monster or item appearing.

    #maximum number of monsters per room
    max_monsters = from_dungeon_level(z, [[1, 0], [2, 5], [2, 10], [3, 15]])

    #chance of each monster
    monster_chances = {}
    monster_chances['kobold'] = from_dungeon_level(z, [[100, 0], [50, 3],  [5, 8],   [0, 13],   [0, 17]   ])
    monster_chances['goblin'] = from_dungeon_level(z, [[5, 0],   [100, 3], [50, 8],  [5, 13],   [0, 17]   ])
    monster_chances['orc'] = from_dungeon_level(z,    [[0, 0],   [5, 3],   [100, 8], [50, 13],  [5, 17]   ])
    monster_chances['human'] = from_dungeon_level(z,  [[0, 0],   [0, 3],   [5, 8],   [100, 13], [50, 17]  ])
    monster_chances['elf'] = from_dungeon_level(z,    [[0, 0],   [0, 3],   [0,8],    [5, 13],   [100, 17] ])
    
    
    #maximum number of items per room
    max_items = from_dungeon_level(z, [[1, 0], [2, 7]])

    #chance of each item (by default they have a chance of 0 at level 1, which then goes up)
    item_chances = {}
    item_chances['potions'] = from_dungeon_level(z, [[20, 0]])
    item_chances['scrolls'] = from_dungeon_level(z, [[20, 0]])
    item_chances['wands'] = from_dungeon_level(z, [[10, 0]])
    item_chances['weapons'] = from_dungeon_level(z, [[10, 0]])
    item_chances['armor'] = from_dungeon_level(z, [[5, 0]])
    item_chances['glasses'] = from_dungeon_level(z, [[10, 0]])
    item_chances['spellbooks'] = from_dungeon_level(z, [[10, 0]])
    item_chances['rings'] = from_dungeon_level(z, [[10, 0]])
    
    potions = {}
    potions['potion of magma'] = from_dungeon_level(z, [[20, 0]])
    potions['potion of invisibility'] = from_dungeon_level(z, [[10, 0]])
    potions['potion of healing'] = from_dungeon_level(z, [[30, 0]])
    potions['potion of tangerine juice'] = from_dungeon_level(z, [[25, 0]])
    potions['potion of berserk rage'] = from_dungeon_level(z, [[15, 0]])
    
    scrolls = {}
    scrolls['scroll of earth'] = from_dungeon_level(z, [[15, 0]])
    scrolls['scroll of identify'] = from_dungeon_level(z, [[25, 0]])
    scrolls['scroll of teleport'] = from_dungeon_level(z, [[20, 0]])
    scrolls['scroll of enchantment'] = from_dungeon_level(z, [[10, 0]])
    scrolls['scroll of light'] = from_dungeon_level(z, [[30, 0]])
    
    wands = {}
    wands['wand of digging'] = from_dungeon_level(z, [[30, 0]])
    wands['wand of fireball'] = from_dungeon_level(z, [[20, 0]])
    wands['wand of air'] = from_dungeon_level(z, [[25, 0]])
    wands['wand of waterjet'] = from_dungeon_level(z, [[15, 0]])
    wands['wand of polymorph'] = from_dungeon_level(z, [[10, 0]])
    
    weapons = {}
    weapons['dagger'] = from_dungeon_level(z, [[30, 0]])
    weapons['sword'] = from_dungeon_level(z, [[25, 0]])
    weapons['staff'] = from_dungeon_level(z, [[20, 0]])
    weapons['mace'] = from_dungeon_level(z, [[15, 0]])
    weapons['zweihander'] = from_dungeon_level(z, [[10, 0]])
    
    armor = {}
    armor['cloth armor'] = from_dungeon_level(z, [[30, 0]])
    armor['leather armor'] = from_dungeon_level(z, [[25, 0]])
    armor['chain armor'] = from_dungeon_level(z, [[20, 0]])
    armor['plate armor'] = from_dungeon_level(z, [[20, 0]])
    armor['mithril armor'] = from_dungeon_level(z, [[5, 0]])
    
    glasses = {}
    glasses['lenses of see invisible'] = from_dungeon_level(z, [[20, 0]])
    glasses['nerd glasses'] = from_dungeon_level(z, [[25, 0]])
    glasses['Xray visor'] = from_dungeon_level(z, [[15, 0]])
    glasses['glasses of telepathy'] = from_dungeon_level(z, [[10, 0]])
    glasses['sunglasses of elemental protection'] = from_dungeon_level(z, [[30, 0]])
    
    rings = {}
    rings['ring of fire resistance'] = from_dungeon_level(z, [[20, 0]])
    rings['ring of strength'] = from_dungeon_level(z, [[30, 0]])
    rings['hunger ring'] = from_dungeon_level(z, [[25, 0]])
    rings['ring of invisibility'] = from_dungeon_level(z, [[10, 0]])
    rings['lucky ring'] = from_dungeon_level(z, [[15, 0]])
    
    spellbooks = {}
    spellbooks['book of healing'] = from_dungeon_level(z, [[15, 0]])
    spellbooks['book of waterjet'] = from_dungeon_level(z, [[20, 0]])
    spellbooks['book of sunfire'] = from_dungeon_level(z, [[25, 0]])
    spellbooks['book of make tangerine potion'] = from_dungeon_level(z, [[10, 0]])
    spellbooks['book of weakness'] = from_dungeon_level(z, [[30, 0]])
    
    
    #choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, max_monsters)
    
    for i in range(num_monsters):
        #choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        #only place it if the tile is not blocked
        #if not is_blocked(x, y, z):
        #choose the monster
        choice = random_choice(monster_chances)
        #create the monster
        monster = create_monster(choice, x, y, z)
        
        objects[z].append(monster)
        SUM += monster.fighter.xp
        
    #choose random number of items
    num_items = libtcod.random_get_int(0, 0, max_items)

    for i in range(num_items):
        #choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        #only place it if the tile is not blocked
        #if not is_blocked(x, y, z):
        choice = random_choice(item_chances)
        if choice == 'potions':
            POT += 1
            choose = random_choice(potions)
        elif choice == 'scrolls':
            choose = random_choice(scrolls)
            SCR += 1
        elif choice == 'wands':
            choose = random_choice(wands)
            WAN += 1
        elif choice == 'weapons':
            choose = random_choice(weapons)
            WEA += 1
        elif choice == 'armor':
            choose = random_choice(armor)
            ARM += 1
        elif choice == 'glasses':
            choose = random_choice(glasses)
            GLA += 1
        elif choice == 'rings':
            choose = random_choice(rings)
            RIN += 1
        elif choice == 'spellbooks':
            choose = random_choice(spellbooks)
            BOO += 1

        choose = string.replace(choose, ' ', '_')
        item = create_item(choose, x, y, z)
        objects[z].append(item)
        item.send_to_back()
        
    #special rooms
    
        
#-----------------------------------------------------------------------------------------------------------------            
            
def get_names_under_cursor(x,y):
    #return a string with the names of all objects under the mouse or crosshair
    T.layer(2)
    T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
    
    #create a list with the names of all objects at the mouse's coordinates and in FOV
    # names = [obj.name for obj in reversed(objects[player.z])
             # if obj.x == x and obj.y == y and visible_to_player(x,y)]
    names = []
    for obj in reversed(objects[player.z]):
        if obj.x == x and obj.y == y and visible_to_player(x,y):
            names.append(obj.name)
        
    #get terrain type unter mouse (terrain, walls, etc..)
    if visible_to_player(x,y):
        if not map[player.z][x][y].name == 'empty':
            names.append(map[player.z][x][y].name)
        
    if names:
       
        pile = names
        i = 0
        for thing in pile:    
            pos = x+1
            #if x >= 60:
            if x + len(thing) >= SCREEN_WIDTH:
                pos = x-len(thing)
            T.print_(pos, y+i+1, thing)
            i += 1        
    T.layer(0)
    
    #-----------------------------------------------------------------------------------------------
    
    
def render_all():
    global fov_map, fov_recompute, light_map, l_map 

    T.layer(0)
    
    #if fov_recompute:
    #recompute FOV if needed (the player moved or something)
    #fov_recompute = False
    vision = 100
    libtcod.map_compute_fov(fov_map, player.x, player.y, vision, FOV_LIGHT_WALLS, FOV_ALGO)
    T.clear()
    
    T.bkcolor(adjust_bk_color())
    
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
                 
            if not visible_to_player(x,y):
                #if it's not visible right now, the player can only see it if it's explored
                if map[player.z][x][y].explored:
                    T.print_(x, y, '[color=' + map[player.z][x][y].color_dark + ']' + map[player.z][x][y].char_dark)
            else:
                #it's visible
                color_a = map[player.z][x][y].color_light
                
                if get_equipped_in_slot('eyes', player):
                    if map[player.z][x][y].trail:
                        color_a = 'lime'
                    else:
                        color_a = map[player.z][x][y].color_dark
                
                T.print_(x, y, '[color=' + color_a + ']' + map[player.z][x][y].char_light)
                
    #draw all objects in the list, except the player. we want it to
    #always appear over all other objects! so it's drawn later.
    for object in objects[player.z]:
        if object != player:
            object.draw()
    player.draw()
    
    T.bkcolor('black')
                
#------------------------------------------------------------------------------------------ 
    # #prepare to render the GUI panel
    T.layer(1)
    T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
    #print the game messages, one line at a time
    y = 1
    for (line, color) in game_msgs:
        T.color(color)
        T.print_(MSG_X, y + PANEL_Y, line)
        y += 1
#------------------------------------------------------------------------------------------  
    #player stats
    location = 'Kobrade Hills'
    if player.z >= 65 and player.z< 98:
        location = 'The Sky'
    elif player.z >= 41 and player.z< 49:
        location = 'The Sewers'
    elif player.z >= 30 and player.z< 41:
        location = 'The Dungeon'
    elif player.z >= 18 and player.z< 30:
        location = 'The Underground City'
    elif player.z >= 10 and player.z< 18:
        location = 'The Fiery Depths'
    elif player.z >= 5 and player.z< 10:
        location = '??'
    elif player.z >= 0 and player.z< 5:
        location = 'The Abyss'
    
    if is_in('church coordinates'):
        location = 'The Locked Church'
    
    if is_in('castle coordinates'):
        location = 'The Castle in the Sky'
    
    T.print_(13,24, '[color=white]' + location)
    
    if get_equipped_in_slot('left hand', player): 
        T.print_(1,24, '[color=white]Compass: \n x=' + str(player.x) + '\n y=' + str(player.y) + '\n z=' + str(player.z-50))
    
    # HUD
    hud = []
    for y in range(-1,2):
        for x in range(-1,2):
            try:
                if map[player.z+1][player.x+x][player.y+y].type == 'sky' or map[player.z+1][player.x+x][player.y+y].type == 'air':
                    hud.append('-')
                elif map[player.z+1][player.x+x][player.y+y].type == 'empty' or map[player.z+1][player.x+x][player.y+y].type == 'grass' or map[player.z+1][player.x+x][player.y+y].type == 'rubble':
                    hud.append('.')
                elif map[player.z+1][player.x+x][player.y+y].type == 'water' or map[player.z+1][player.x+x][player.y+y].type == 'lava':
                    hud.append('~')
                else:
                    hud.append('#')
            except:
                hud.append('#')
    
    i = ''.join(hud)
    T.color('white')
    T.print_(40, 24, 'View up')
    T.print_(42, 25, i[0]+i[1]+i[2])
    T.print_(42, 26, i[3]+i[4]+i[5])
    T.print_(42, 27, i[6]+i[7]+i[8])
    
#--------------------------------------------------------------------------------------------------------------------------        
    #get info under mouse as console window attached to the mouse pointer
    (x, y) = (T.state(T.TK_MOUSE_X), T.state(T.TK_MOUSE_Y))
    get_names_under_cursor(x,y)
    T.layer(0)
    
def is_in(location):
    (x,x2,y,y2,z,z2) = parameters[location]
    if player.z >= z and player.z < z2:
        if player.x >= x and player.x <= x2:
            if player.y >= y and player.y <= y2:
                return True
    return False

def adjust_bk_color():
    #introduces the color tone 'sky' depending on altitude                
    if player.z >= 60:    
        lvl = (player.z - 50) / 75.00
        if lvl > 1 or player.z == 98:
            lvl = 1
        color_alt = libtcod.color_lerp ( libtcod.black, libtcod.sky, lvl)
    
        color_bk = str(T.color_from_argb(0, color_alt[0], color_alt[1], color_alt[2]))
    
    elif player.z <= 25 and player.z >= 10:
        lvl = (30 - player.z) / 75.00
        if lvl > 1:
            lvl = 1
        color_alt = libtcod.color_lerp ( libtcod.black, libtcod.red, lvl)
    
        color_bk = str(T.color_from_argb(0, color_alt[0], color_alt[1], color_alt[2]))
        
    else:
        lvl = 0
        
        color_alt = libtcod.color_lerp ( libtcod.black, libtcod.sky, lvl)
    
        color_bk = str(T.color_from_argb(0, color_alt[0], color_alt[1], color_alt[2]))
    
    return color_bk
    
def visible_to_player(x,y, monster=None):
    if libtcod.map_is_in_fov(fov_map, x, y): #is in fov?
        return True
    return False
  
def make_GUI_frame(x, y, dx, dy, color='white'):
    #sides
    T.layer(4)
    for i in range(dx-1):
        T.print_(i+x, 0+y, '[color=' + color + ']' + '[U+2500]')
    for i in range(dx-1):
        T.print_(i+x, dy-1+y, '[color=' + color + ']' + '[U+2500]')
    for i in range(dy-1):
        T.print_(0+x, i+y, '[color=' + color + ']' + '[U+2502]')
    for i in range(dy-1):
        T.print_(dx-1+x, i+y, '[color=' + color + ']' + '[U+2502]')

    #corners
    T.print_(x, y, '[color=' + color + ']' + '[U+250C]')
    T.print_(dx-1+x, y, '[color=' + color + ']' + '[U+2510]')
    T.print_(x, dy-1+y, '[color=' + color + ']' + '[U+2514]')
    T.print_(dx-1+x, dy-1+y, '[color=' + color + ']' + '[U+2518]')
    T.layer(0)
    
    
def message(new_msg, color = 'white'):
    #split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
    
        #if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]

        #add the new line as a tuple, with the text and the color
        game_msgs.append( (line, color) )


def player_move_or_attack(dx, dy):
    global fov_recompute

    #the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy

    #try to find an attackable object there
    target = None
    npc = None
    for object in objects[player.z]:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break
            
    #attack if target found, move otherwise
    if target is not None:
        player.fighter.attack(target)
        fov_recompute = True
    else:
        player.move(dx, dy)
        fov_recompute = True
        
def menu(header, options, width, back=None, x1=0, y1=0):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
    
    #calculate total height for the header (after auto-wrap) and one line per option
    header_height = header.count('\n')
    if header == '':
        header_height = 0
    height = len(options) + header_height + 1

    if x1 == 0 and y1 == 0:
        x = SCREEN_WIDTH / 2 - width / 2
        y = SCREEN_HEIGHT / 2 - height / 2
    else:
        x = x1
        y = y1
        
    T.layer(2)
    
    #make_GUI_frame(x, y, width, height)
    
    #cursors position
    c_pos = 0
    
    output = None
    
    while True:
        T.layer(2)
        T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
        
        #create an off-screen console that represents the menu's window
        if back:
            T.composition(T.TK_ON)
            for i in range(width):
                for j in range(height):
                    T.print_(i+x,j+y, '[color=' + back + ']' + '[U+2588]')
        
        T.print_(x+1,y, '[color=white]' + header)
        
        #print all the options
        h = header_height
        letter_index = ord('a')
        run = 0
        for option_text in options:
            text = option_text
            
            if run == c_pos:
                T.print_(x+1,h+y+1, '[color=yellow]> ' + text)
                
            else:    
                T.print_(x+1,h+y+1, '[color=white] ' + text)
            h += 1
            letter_index += 1
            run += 1
            
        #present the root console to the player and wait for a key-press
        T.refresh()
        
        key = T.read()
        if key == T.TK_ESCAPE:
            break
        elif key == T.TK_UP or key == T.TK_KP_8:
            c_pos -= 1
            if c_pos < 0:
                c_pos = len(options)-1
                
        elif key == T.TK_DOWN or key == T.TK_KP_2:
            c_pos += 1
            if c_pos == len(options):
                c_pos = 0
        
        elif key == T.TK_ENTER:               
            #convert the ASCII code to an index; if it corresponds to an option, return it
            index = c_pos
            #if index >= 0 and index < len(options): 
            output = index
            break
            
    T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
    T.composition(T.TK_OFF)
    T.layer(0)
    return output
    
def inventory_menu(header):
    #show a menu with each item of the inventory as an option
    if len(player.fighter.inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in player.fighter.inventory:
            text = item.name
            #show additional information, in case it's equipped
            if item.equipment and item.equipment.is_equipped:
                text = text + ' (on ' + item.equipment.slot + ')'
            options.append(text)

    index = menu(header, options, INVENTORY_WIDTH, 'black', 1, 1)

    #if an item was chosen, return it
    if index is None or len(player.fighter.inventory) == 0: return None
    return player.fighter.inventory[index].item
    
def item_use_menu(item):
    #show a menu with each possible use of an item as an option
    
    header = 'What do you want to do with ' + item.owner.name + '?\n'
    
    options = ['cancel', 'drop', 'throw']
    if item.use_function:
        options.append('use')
    if item.owner.equipment: 
        if item.owner.equipment.is_equipped:
            options.append('dequip')
        else:
            options.append('equip')
    
    index = menu(header, options, INVENTORY_WIDTH, 'black', 1, 1)

    if index:
        #if an item was chosen, return resp option
        return options[index]

def msgbox(text, width=50):
    menu(text, [], width,  back = 'black', x1 = 0, y1 = 1)  #use menu() as a sort of "message box"
    
def enter_text_menu(header, max_length): #many thanks to Aukustus and forums for poviding this code. 
    #clear_screen()
    
    T.layer(2)
    T.clear_area(0,0, SCREEN_WIDTH, SCREEN_HEIGHT)
   
    T.print_(5, 4, '[color=white]' + header)
    
    T.print_(5, 5, '[color=white]Name: ')
    key = 0
    letter = ''
    output = ''
    waste, output = T.read_str(12,5, letter, max_length)    
    return output
    

def handle_keys():
    global key, stairs, upstairs, ladder, upladder, game_state, FONT_SIZE
    
    if key == T.TK_ESCAPE:
        choice = menu('Do you want to quit?', ['Yes', 'No'], 24,'black', SCREEN_WIDTH / 2 - 12, 7 )
        if choice == 0:                
            game_state = 'exit' #<- lead to crash WHY ??
            return 'exit' #exit game
        else:
            return 'didnt-take-turn'

    if game_state == 'playing':
        #movement keys
        if key == T.TK_UP or key == T.TK_KP_8:
            player_move_or_attack(0, -1)
        elif key == T.TK_DOWN or key == T.TK_KP_2:
            player_move_or_attack(0, 1)
        elif key == T.TK_LEFT or key == T.TK_KP_4:
            player_move_or_attack(-1, 0)
        elif key == T.TK_RIGHT or key == T.TK_KP_6:
            player_move_or_attack(1, 0)
        elif key == T.TK_HOME or key == T.TK_KP_7:
            player_move_or_attack(-1, -1)
        elif key == T.TK_PAGEUP or key == T.TK_KP_9:
            player_move_or_attack(1, -1)
        elif key == T.TK_END or key == T.TK_KP_1:
            player_move_or_attack(-1, 1)
        elif key == T.TK_PAGEDOWN or key == T.TK_KP_3:
            player_move_or_attack(1, 1)
        elif key == T.TK_KP_5 or key == T.TK_W:
            return 1
        elif key == T.TK_SPACE:
            player_jump()
            return 'jump'
        else:
            #test for other keys
            if key == T.TK_G:
                #pick up an item
                for object in reversed(objects[player.z]):  #look for an item in the player's tile
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pick_up(player)
                        return 0
                    elif object.x == player.x and object.y == player.y and object.name == 'fountain':
                        choice = menu('Do you want to drink from the fountain?', ['Yes','No'], 40)
                        if choice == 0:
                            drink_fountain()
                            return 0
                        elif choice == 1:
                            pass
                            
            if key == T.TK_O:
                FONT_SIZE += 1
                T.set("font: courbd.ttf, size=" + str(FONT_SIZE))
            
            if key == T.TK_P:
                FONT_SIZE -= 1
                T.set("font: courbd.ttf, size=" + str(FONT_SIZE))
            
            if key == T.TK_X:
                pass
                # libtcod.line_init(1, 1, 10, 10)
                # while True:
                    # (a, b) = libtcod.line_step()
                    # print a, b
                    # if not a:
                        # break
    
            if key == T.TK_H:
                msgbox('''
Controls:\nMOVE in 8 directions\nJUMP with SPACE\ng grab item\ni inventory\no,p screen bigger,smaller\nESC quit,exit\nENTER confirm\n

The 'View up' are the nine squares above you.\nThe middle one is directly above the avatar.\nIf it is '-' you can jump.\nIf it is '#' it is blocked.\nIf it is '~' you are under water. 
\n\n\n\n\n\n''')
            
            if key == T.TK_I:
            #show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('Choose item from your inventory or ESC to cancel.\n')
                if chosen_item is not None:
                    #chosen_item.use(player)
                    decide = item_use_menu(chosen_item)
                    
                    if not decide:
                        return 'didnt-take-turn'
                    
                    if decide == 'drop':
                        chosen_item.drop(player)
                    elif decide == 'throw':
                        chosen_item.throw(player)
                        initialize_fov()
                    elif decide == 'use':
                        chosen_item.use(player)
                    elif decide == 'equip' or decide == 'dequip':
                        chosen_item.owner.equipment.toggle_equip(player)
                    elif decide == 'name':
                        name = enter_text_menu('How do you want to call ' + chosen_item.owner.name +'?',25)
                        ident_table[chosen_item.owner.base_name] = ident_table[chosen_item.owner.base_name] + ' named ' + name
                        #naming menue
                    
                    return 0

            # if key == T.TK_R:
                # up()
                
            # if key == T.TK_T:
                # down()
                        
            return 'didnt-take-turn'

def give_length(thing):
    i = 0
    for part in thing:
        i += 1
    return i
            
                    
def throw_effect(x1, y1, x2, y2, color, char):
    render_all()
    libtcod.line_init(x1, y1, x2, y2)
    while True:
        (a, b) = libtcod.line_step()
        T.layer(3)
        T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
        T.print_(a, b, '[color=' + color +  ']' + char)
        if not a: 
            break
        T.refresh()
        T.layer(0)
        T.delay(50)
        
def fight_effect(cx, cy, color, char):
    render_all()
    num_frames = LIMIT_FPS
    for frame in range(10):
        T.layer(1)
        T.print_(cx, cy, '[color=' + color + ']' + char)
        T.refresh()
        render_all()
    T.layer(0)
    T.clear()
    render_all()
        
def spell_effect(cx, cy, color, char):
    render_all()
    num_frames = LIMIT_FPS
    for frame in range(10):
        T.layer(1)
        T.print_(cx+1, cy, '[color=' + color + ']' + '?')
        T.print_(cx-1, cy, '[color=' + color + ']' + '?')
        T.print_(cx, cy+1, '[color=' + color + ']' + '?')
        T.print_(cx, cy-1, '[color=' + color + ']' + '?')
        T.refresh()
        render_all()
    T.layer(0)
    T.clear()
    render_all()
        
            
def player_death(player):
    #the game ended!
    global game_state
    #in case it gets called on many events happening the same loop
    if game_state == 'dead':
        return
    
    #identify all items
    for key, value in ident_table.iteritems():
        ident_table[key] = 0

    message('--You died!', 'red')
    game_state = 'dead'
    
    #for added effect, transform the player into a corpse!
    player.char = '%'    
    player.color = 'dark red'
    render_all()
    T.refresh()
    #show inventory
    chosen_item = inventory_menu('Your possessions are identified.\n')
    #show conducts
    msgbox('You \n' + conducts['conduct1'] + '\n' + conducts['conduct2'] + '\n' + conducts['conduct3'] + '\n' + conducts['conduct4'] + '\n' + conducts['conduct5'] + '\n')
    
def monster_death(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    message('The ' + monster.name + ' is dead, you gain ' + str(monster.fighter.xp) + ' xp!', 'yellow')
    
    for item in monster.fighter.inventory:
        if item.equipment:
            if item.equipment.is_equipped and libtcod.random_get_int(0,0,100) <= 20:
                item.item.drop(monster)
    
    #break pacifist conduct
    conducts['conduct5'] = ''
    
    # if libtcod.random_get_int(0,0,100) < 33:
        # return monster.delete()
    
    player.fighter.xp += monster.fighter.xp
    monster.char = '%'
    monster.color = 'dark red'
    monster.blocks = False
    
    monster.fighter = None
    monster.ai = None
    monster.base_name = 'remains of ' + monster.base_name

    item_component = Item(use_function=None) #use tbd
    monster.item = item_component 
    monster.item.owner = monster #monster corpse can be picked up
    
    if is_blocked(monster.x, monster.y, monster.z):
        monster.delete()
    
    # resulted in a bug. Player was dying by explosion of Goblin Alchemist -> list.remove(x): x not in list
    try:
        monster.send_to_back()
    except:
        pass
    
DEATH_DICT = {
    'monster_death': monster_death
    }

def distance_2_point(x1, y1, x2, y2):
        #return the distance to another object
        dx = x2 - x1
        dy = y2 - y1
        return math.sqrt(dx ** 2 + dy ** 2)
        
def target_ball(max_range=None):
    global key, mouse
    #return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    (x, y) = (player.x, player.y)
    while True:
        #render the screen. this erases the inventory and shows the names of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        render_all()
       
        if mouse.dx:
            (x, y) = (mouse.cx, mouse.cy)

        (x, y) = key_control_target(x, y, key)        
            
        libtcod.console_set_default_foreground(0, libtcod.red)
        i = player.fighter.firepower() + 1
        for y2 in range(MAP_HEIGHT):
            for x2 in range(MAP_WIDTH):
                if distance_2_point(x, y, x2, y2) <= i and visible_to_player(x2,y2) and visible_to_player(x,y):
                    libtcod.console_put_char(0, x2, y2, chr(7), libtcod.BKGND_NONE)
        
        
        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            message('Canceled.')
            return (None, None)  #cancel if the player right-clicked or pressed Escape

        #accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
        if ( (key.vk == libtcod.KEY_ENTER or mouse.lbutton_pressed) and visible_to_player(x,y) and
                (max_range is None or player.distance(x, y) <= max_range)):
            return (x, y)    
    
def target_line(max_range=None):
    global key, mouse
    #return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    (x, y) = (player.x, player.y)
    while True:
        #render the screen. this erases the inventory and shows the names of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        render_all()
       
        if mouse.dx:
            (x, y) = (mouse.cx, mouse.cy)
        
        (x, y) = key_control_target(x, y, key)
        
        if not libtcod.map_is_in_fov(fov_map, x, y): continue
        
        for frame in range(LIMIT_FPS):
            libtcod.line_init(player.x, player.y, x, y)
            while True:
                (a, b) = libtcod.line_step()
                if a is None: break
                
                libtcod.console_set_default_foreground(0, libtcod.red)
              
                libtcod.console_put_char(0, a, b, chr(7), libtcod.green)
                
                if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
                    message('Canceled.')
                    return (None, None)  #cancel if the player right-clicked or pressed Escape

                #accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
                if ( (key.vk == libtcod.KEY_ENTER or mouse.lbutton_pressed) and libtcod.map_is_in_fov(fov_map, x, y) and
                        (max_range is None or player.distance(x, y) <= max_range)):
                    return (x, y)
               
def target_tile(max_range=None):
    global key
    #return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    (x, y) = (player.x, player.y)
    while True:
        
        T.refresh()
        render_all()
        
        key = T.read()
        if key == T.TK_MOUSE_MOVE:
            (x, y) = (T.state(T.TK_MOUSE_X), T.state(T.TK_MOUSE_Y))
        
        T.layer(3)
        T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
        T.print_(x-1, y, '-')
        T.print_(x+1, y, '-')
        T.print_(x, y+1, '|')
        T.print_(x, y-1, '|')
        T.layer(0)    
        
        get_names_under_cursor(x,y)
            
        (x, y) = key_control_target(x, y, key)
            
        if key == T.TK_MOUSE_RIGHT or key == T.TK_ESCAPE:
            #message('Canceled.')
            T.layer(3)
            T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
            T.layer(0)
            return (None, None)  #cancel if the player right-clicked or pressed Escape

        #accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
        fighter = False
        for obj in objects[player.z]:
            if obj.x == x and obj.y == y and obj.fighter:
                fighter = True
        if (key == T.TK_MOUSE_LEFT or key == T.TK_ENTER) and (not is_blocked(x,y,player.z) or fighter):
            T.layer(3)
            T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
            T.layer(0)
            return (x, y)    
 
def key_control_target(a, b, key):
    (x, y) = 0, 0
    if key == T.TK_UP or key == T.TK_KP_8:
        y -= 1
    elif key == T.TK_DOWN or key == T.TK_KP_2:
        y += 1
    elif key == T.TK_LEFT or key == T.TK_KP_4:
        x -= 1        
    elif key == T.TK_RIGHT or key == T.TK_KP_6:
        x += 1    
    # elif key.vk == libtcod.KEY_HOME or key.vk == libtcod.KEY_KP7 or chr(key.c) == 'z':
        # x -= 1
        # y -= 1
    # elif key.vk == libtcod.KEY_PAGEUP or key.vk == libtcod.KEY_KP9 or chr(key.c) == 'u':
        # x += 1
        # y -= 1
    # elif key.vk == libtcod.KEY_END or key.vk == libtcod.KEY_KP1 or chr(key.c) == 'b':
        # x -= 1
        # y += 1
    # elif key.vk == libtcod.KEY_PAGEDOWN or key.vk == libtcod.KEY_KP3 or chr(key.c) == 'n':
        # x += 1
        # y += 1
    return a+x, b+y
            
def target_monster(max_range=None):
    #returns a clicked monster inside FOV up to a range, or None if right-clicked
    while True:
        (x, y) = target_tile(max_range)
        if x is None:  #player cancelled
            return None

        #return the first clicked monster, otherwise continue looping
        for obj in objects[player.z]:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj

def closest_monster(max_range):
    #find closest enemy, up to a maximum range, and in the player's FOV
    closest_enemy = None
    closest_dist = max_range + 1  #start with (slightly more than) maximum range

    for object in objects[player.z]:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            #calculate distance between this object and the player
            dist = player.distance_to(object)
            if dist < closest_dist:  #it's closer, so remember it
                closest_enemy = object
                closest_dist = dist
    return closest_enemy


def monsters_around(center, range):
    #find all monsters around in range radius and visible
    monsters = []
    
    for object in objects[player.z]:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            #calculate distance between this object and the player
            dist = center.distance_to(object)
            if dist < range + 1:
                monsters.append(object)
    return monsters

def beings_around(x, y, range):
    #find all monsters around in range radius and visible
    monsters = []
    
    for object in objects[player.z]:
        if object.fighter:
            #calculate distance between this object and the player
            dist = distance_2_point(x, y, object.x, object.y)
            if dist < range + 1:
                monsters.append(object)
    return monsters
    
def save_game():
    #open a new empty shelve (possibly overwriting an old one) to write the game data
    file = shelve.open('savegame', 'n')
    file['map'] = map
    file['objects'] = objects
    file['player_index1'] = player.z  #index of player in objects list
    file['player_index2'] = objects[player.z].index(player)
    #file['stairs_index'] = objects.index(stairs)  #same for the stairs
    file['game_msgs'] = game_msgs
    file['game_state'] = game_state
    #file['dungeon_level'] = dungeon_level
    file.close()
    
def unsave_game():
    #open a new empty shelve (possibly overwriting an old one) to clear the game data
    file = shelve.open('savegame', 'n')
    file['map'] = 0
    file['objects'] = 0
    file['player_index1'] = 0 #index of player in objects list
    file['player_index2'] = 0 
    #file['stairs_index'] = objects.index(stairs)  #same for the stairs
    file['game_msgs'] = 0
    file['game_state'] = 0
    #file['dungeon_level'] = 0
    file.close()

def load_game():
    #open the previously saved shelve and load the game data
    global map, objects, player, game_msgs, game_state
    file = shelve.open('savegame', 'r')
    map = file['map']
    objects = file['objects']
    player = objects[file['player_index1']][file['player_index2']]  #get index of player in objects list and access it
    #stairs = objects[file['stairs_index']]  #same for the stairs
    game_msgs = file['game_msgs']
    game_state = file['game_state']
    #dungeon_level = file['dungeon_level']
    file.close()
    
    unsave_game() #clears savegame file

    initialize_fov()

    
def create_player():
    #create object representing the player
    fighter_component = Fighter(hp=5, 
                                damage=0, 
                                armor=0, 
                                wit=5, 
                                strength=5, 
                                spirit=5,
                                death_function=player_death)
    ai_component = PlayerAI(ticker, 6)
    player = Object(10, 10, 50, '@', 'You', 'white', blocks=True, fighter=fighter_component, ai=ai_component)
    
    i = create_item('jumping_boots')
    player.fighter.inventory.append(i)
    i.equipment.toggle_equip(player)
    j = create_item('compass')
    player.fighter.inventory.append(j)
    #j.equipment.toggle_equip(player)
    
    # k = create_item('hunting_glasses')
    # player.fighter.inventory.append(k)
    
    
    return player
    
        
class Physics:
    def __init__(self, ticker, duration):
        self.ticker = ticker
        self.duration = duration
        self.ticker.schedule_turn(self.duration, self)
        
    def take_turn(self):
        
        for list in objects:
            if list != []:
                for object in list:
                    if object.item: 
                        if map[object.z][object.x][object.y].type == 'sky' or map[object.z][object.x][object.y].type == 'air': 
                            if object != player:
                                objects[object.z - 1].append(object)
                                objects[object.z].remove(object)
                                object.z -= 1 
            
    
        self.ticker.schedule_turn(self.duration, self)
        
def new_game():
    global player, game_msgs, game_state, objects, ticker, parameters
    
    T.layer(0)
    T.clear()
    T.color('white')
    
    T.print_(3, 0, '''[align=left]
Up and down and up again
Through the sky and through the den

The cat has boots
Up high it shoots
From there it loots
What has been locked

Down low it falls
Where footstep halls
Where water halts
No slit is blocked

Up and down and up again
On the throne and then you win

Where daddies died
Where fire fried
And vision lied
Without an end

Jump jump up high
With boots that fly
You'll reach the sky
And will ascend

 --Hopscotch song of kids in Kobrade Village
    ''')
    T.layer(1)
    T.color('yellow')
    T.print_(SCREEN_WIDTH-1, SCREEN_HEIGHT-1, '[align=right]Loading...')
     
    T.refresh()

    while True:
        ticker = timer.Ticker()
        
        physics = Physics(ticker, 6)
        
        objects = [ [] for i in range(MAP_Z)] #levels
        
        parameters = {

        'number of trees': 0,
        'church': 0,
        'church door': 0,
        'connection sewers': 0,
        'throne': 0
            }
    
        make_map()
        
        if parameters['number of trees'] >= 2 and parameters['church'] == 1 and parameters['connection sewers'] == 1:
            break
    
    o = create_item('winged_boots', libtcod.random_get_int(0,5,MAP_WIDTH-5), libtcod.random_get_int(0,3,MAP_HEIGHT-3),0 )
    objects[0].append(o)
    
    
    player = create_player()    
    
    objects[player.z].append(player)
    
    while True:
        x = libtcod.random_get_int(0,0,MAP_WIDTH)
        y = libtcod.random_get_int(0,0,MAP_HEIGHT)
        
        if not is_blocked(x,y,player.z): 
            player.x = x
            player.y = y
            if not is_in('church coordinates'):
                break
    
    for room in parameters['rooms']:
        x,y = room.center()
        if map[20][x][y].type == 'empty':
            x2,y2 = x,y
            break
    
    objects[20].append(create_item('bones', x2, y2, 20 ))
    objects[20].append(create_item('key', x2, y2, 20 ))
    
    
    # # #-------------------------------------------------------------------------
    # libtcod.console_set_custom_font('terminal12x12_gs_ro.png', libtcod.FONT_LAYOUT_ASCII_INROW)
    # libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'TSADOKH SCREEN', False)#, libtcod.RENDERER_OPENGL)
    # libtcod.sys_set_fps(LIMIT_FPS)
    # con = libtcod.console_new(MAP_HEIGHT, MAP_Z)
    # for f in range(0, MAP_HEIGHT):
        # for g in range(0, MAP_Z):
            # try:
                # u = map[g][25][f].char_light
                # # if 'U' in u:
                    # # u = 'x'
                # if u != '.':
                    # u = '#'
                
                # c = map[g][25][f].color_light
                # #print c
                # d = 'white' #c.replace(" ", "_")
                # #print d
                # libtcod.console_put_char_ex(con, f, g, u, getattr(libtcod, d), libtcod.black)
                
            # except:
                # libtcod.console_put_char_ex(con, f, g, 'x', libtcod.white, libtcod.black)
    
    # pix = libtcod.image_from_console(con)
    # libtcod.image_save(pix,"mypic.bmp")
    # # #-------------------------------------------------------------------------
    
    T.print_(SCREEN_WIDTH-1, SCREEN_HEIGHT-1, '[align=right]Press ENTER to continue')
    T.refresh()
    
    while True:
        key = T.read()
        if key == T.TK_ENTER:
            break
    
    initialize_fov()

    game_state = 'playing'

    #create the list of game messages and their colors, starts empty
    game_msgs = []

    z_consistency() #general clean-up to set all z-coordinates of all items and objects
    
    #a warm welcoming message!
    message('Welcome to Kobrade Hills! Press h for help.', 'yellow')

def z_consistency():
    global objects
    for i in range(MAP_Z):
        for obj in objects[i]:
            obj.z = i
            if obj.fighter:
                for item in obj.fighter.inventory:
                    item.z = i
    
def set_player_on_upstairs(stair):
    global player
    
    if stair == 'ladder':
        for i in objects[player.z]:
            if i.name == 'upladder':
                player.x = i.x
                player.y = i.y
    else:
        for i in objects[player.z]:
            if i.name == 'upstairs':
                player.x = i.x
                player.y = i.y

def up():
    
    objects[player.z + 1].append(player)
    objects[player.z].remove(player)
    player.z += 1
    initialize_fov()

def down():
    
    objects[player.z - 1].append(player)
    objects[player.z].remove(player)
    player.z -= 1
    initialize_fov()

                
def player_jump():
    global player
    
    if player.z == 98:
        return
    
    if not get_equipped_in_slot('feet', player):
        return
    elif get_equipped_in_slot('feet', player).owner.base_name == 'jumping boots':
        pass
    
    if not (map[player.z+1][player.x][player.y].type == 'sky' or map[player.z+1][player.x][player.y].type == 'air' or map[player.z+1][player.x][player.y].type == 'water'):
        return

    if get_equipped_in_slot('feet',player).owner.base_name == 'winged boots':
        pass
    else:
        if map[player.z][player.x][player.y].type == 'sky' or map[player.z][player.x][player.y].type == 'air':
            cloud = False
            for obj in objects[player.z]:
                if obj.x == player.x and obj.y == player.y and obj.name == 'cloud':
                    cloud = True
            if not cloud:
                return
            
    objects[player.z + 1].append(player)
    objects[player.z].remove(player)
    player.z += 1
    initialize_fov()

# def fall(object):
    # global player

    # objects[player.z].remove(player)
    
    # if stair == 'stairs':              
        # player.z -= 1  
            
    # objects[player.z].append(player)    
    # set_player_on_downstairs(stair)
    # message('You go up the stairs cautiously.', 'blue')
    
    # z_consistency()
    # initialize_fov()

def initialize_fov():
    global fov_recompute, fov_map
    fov_recompute = True

    #create the FOV map, according to the generated map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[player.z][x][y].block_sight, not map[player.z][x][y].blocked)
    
def play_game():
    global key, mouse, TURN_COUNT
    
    player_action = None
    
    #main loop
    while True:
        if game_state == 'exit':
            break
        
        ticker.ticks += 1
        ticker.next_turn()    
       
def main_menu():
    
    while True:
        #show the background image, at twice the regular console resolution
        T.layer(0)
        T.clear()
        #T.set("0x00A7: shrine.png, align=top-left");
        T.color('white')
        #T.print_(0,0, '[U+00A7]')
        
        # for x in range(SCREEN_WIDTH):
            # for y in range(10):
                # T.print_(x, y, '[color=sky]=')
                
        # for x in range(SCREEN_WIDTH):
            # for y in range(SCREEN_HEIGHT-3,SCREEN_HEIGHT):
                # T.print_(x, y, '[color=grey]#')
        
        
        #show the game's title, and some credits!
        #T.color('yellow')
        T.print_(SCREEN_WIDTH/2, 5, '[align=center]The Sky and Depths of Kobrade Hills')
        T.print_(SCREEN_WIDTH/2, SCREEN_HEIGHT-2, '[align=center][color=green]#[color=white]IOLx3[color=yellow] Game by Jan | v0.9')
        
        T.print_(SCREEN_WIDTH/2-4, SCREEN_HEIGHT-12, '[align=left]MOVE in 8 directions')
        T.print_(SCREEN_WIDTH/2-4, SCREEN_HEIGHT-11, '[align=left]JUMP with SPACE')
        T.print_(SCREEN_WIDTH/2-4, SCREEN_HEIGHT-10, '[align=left]i for inventory')
        T.print_(SCREEN_WIDTH/2-4, SCREEN_HEIGHT-9, '[align=left]g for grabbing item')
        #T.print_(SCREEN_WIDTH/2-4, SCREEN_HEIGHT-8, '[align=left]w for waiting a turn')
        
        options = ['Play a new game', 'Quit']
        
        #show options and wait for the player's choice
        choice = menu('', options, 10, None, SCREEN_WIDTH/2-4, SCREEN_HEIGHT/2 - 4)
        
        if choice == 0:  #new game
            new_game()
            play_game()
     
        elif choice == 1:  #quit
            break
                  
def win():
    global game_state
    T.clear()
    T.layer
    T.color('white')
    T.print_(3, 7, '[align=left]You ascended from the depths \n to the sky of Kobrade hills!')
    T.print_(3, 12, '[align=left]You win!')
    T.color('yellow')
    T.print_(SCREEN_WIDTH-1, SCREEN_HEIGHT-1, '[align=right]Press ENTER to return to main menu')
    T.refresh()
    
    while True:
        key = T.read()
        if key == T.TK_ENTER:
            break
    
    game_state = 'exit' #<- lead to crash WHY ??
    return 'exit' #exit game
                  
T.open()
T.set("window: size=" + str(SCREEN_WIDTH) + "x" + str(SCREEN_HEIGHT) + ', title=TSaDoKH v0.9')
T.set("font: courbd.ttf, size=" + str(FONT_SIZE))
#T.set("terminal: encoding=437")
#T.set("font: terminal16x16_gs_ro.png, size=16x16, codepage=437")

main_menu()

T.close()