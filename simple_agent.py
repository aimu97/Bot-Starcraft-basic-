#py -m pysc2.bin.agent --map Simple64 --agent simple_agent.ZergAgent --agent_race zerg --use_feature_units

from pysc2.agents import base_agent
from pysc2.lib import actions, features, units

import time
import random
import numpy as np
"""
Initialisation des coordonnées de la base et la base enemie
Construction d'un extracteur pour la collecte de gaz (1 ouvrier collecte ce gaz)
Construction de la spawning pools pour permettre de créer des Zerglings ainsi que des Reines. 
Elle permet egalement d'augmenter la puissance de nos unités.
Generer la reine pour la protection des attaques aériennes et injection de la reine pour augmenter diminuer le temps de production des zerglings
les larve sont mutées en Zergling puis, lorsqu'on possède une armée de 18 Zergling on les envoie sur la base enemie jusqu'à ce qu'on ai gagné.


"""


_Select_idle_worker = actions.FUNCTIONS.select_idle_worker.id #drone qui fait rien
_RALLY_UNITS_MINIMAP = actions.FUNCTIONS.Rally_Units_minimap.id # point de ralliement
_TRAIN_Drone_QUICK = actions.FUNCTIONS.Train_Drone_quick.id
_NOT_QUEUED = [0]
_SUPPLY_USED = 3
_SUPPLY_MAX = 4


def position(a):
    l = a.nonzero();
    if (len(l) == 0):
        return []
    y,x = l
    return list(zip(x,y))


class ZergAgent(base_agent.BaseAgent):
    
    def reset(self):
        super(ZergAgent, self).reset()

        self.Base_type =[18,86]
        self.base_position = []
        self.enemy_base = None
        self.building_type = units.Zerg.Hatchery

        self.Base_selected = False
        self.extractor = []
        self.drone_selected = False
        self.drone_in_training = False
        
        self.drone_training_queued = 0
        self.MakeDrone = True
        self.attack = None
        self.gather = False
        self.queen = False 
        self.zerg = False
        self.army_zerg = False
        self.attack = None
        self.queen_selected = False
        self.queen_count = 0
    
    def __init__(self):
        super(ZergAgent, self).__init__()
        
    
    

    def InitBase(self,obs): # set les coordonées des bases alliées et enemies (fonctionne)
        
        camera = obs.observation.feature_minimap.camera
        v = position(camera!=0)
        ownBase = np.mean(v, axis = 0).round();
        
        enemy_base = [63 - ownBase[0],63 - ownBase[1]]
        return (ownBase,enemy_base)


                    
    def selectBuilding(self,obs,unit_type):# selectionne un batiment en fonction du type. Types : units.Zerg.Hatchery, units.Zerg.SpawningPool, ...
    # à noter, cette fonction marche également si l'unité n'est pas un batiment, par exemple units.Zerg.Queen, units.Zerg.Drone
        target = [[el.x,el.y] for el in obs.observation.feature_units if el.unit_type == unit_type]
        target = target[0]
        print(target)
        return actions.FUNCTIONS.select_point("select", target) # on clique à cette position

    def get_units_by_type(self, obs, unit_type): # renvoie la liste des unités d'un certain type. Par exemple, les drones, les zergs ou les Queen.
      return [unit for unit in obs.observation.feature_units if unit.unit_type == unit_type] # on pourra utiliser la liste obtenue pour obtenir les coordonnées des unités

    def can_do(self, obs, action): # observe si une action est disponible, si on peut faire cette action à ce moment. Cela est pratique car ca évite de regarder le gaz et les minerais en plus de la disponibilité de l'action.
      return action in obs.observation.available_actions

    def unit_type_is_selected(self, obs, unit_type): # verifie si l'unité est bien selectionnée
      if (len(obs.observation.single_select) > 0 and obs.observation.single_select[0].unit_type == unit_type):
        return True
    
      if (len(obs.observation.multi_select) > 0 and obs.observation.multi_select[0].unit_type == unit_type):
        return True
        
      return False  
  

    def step(self, obs):
        
        super(ZergAgent, self).step(obs)
        player = obs.observation.player
        mineral = player.minerals
        player_y, player_x = (obs.observation.feature_minimap.player_relative == features.PlayerRelative.SELF).nonzero()

        if len (self.base_position) == 0:
            self.base_position,self.enemy_base = self.InitBase(obs)[0],self.InitBase(obs)[1]
            print (self.base_position,self.enemy_base)

        """
        obs.first = vérifie s’il s’agit de la première étape du jeu

        """
        if obs.first():
          self.attack = self.enemy_base


        zerg = self.get_units_by_type(obs,units.Zerg.Zergling)

        # on crée des groupes de zerglings qu'on envoie attaquer
        if len(zerg) >= 18 :
          if self.unit_type_is_selected(obs,units.Zerg.Zergling):
            if self.can_do(obs,actions.FUNCTIONS.Attack_minimap.id):
                print("cord",self.enemy_base)
                return actions.FUNCTIONS.Attack_minimap("now", self.enemy_base)
          if self.can_do(obs, actions.FUNCTIONS.select_army.id):
            return actions.FUNCTIONS.select_army("select")
        


          
        # Construction d'un spawning pool 

        spawning_pools = self.get_units_by_type(obs, units.Zerg.SpawningPool)
        if len(spawning_pools) == 0:
          if self.unit_type_is_selected(obs,units.Zerg.Drone):
            if self.can_do(obs, actions.FUNCTIONS.Build_SpawningPool_screen.id):
                if self.base_position[0] < 31:
                    x = 70
                    y = 40
                else:
                    x = 10
                    y = 38

          
                return actions.FUNCTIONS.Build_SpawningPool_screen("now", (x, y))

          # selectionne un drone
          drones = self.get_units_by_type(obs, units.Zerg.Drone)
          if len(drones) > 0:
            drone = random.choice(drones)

            return actions.FUNCTIONS.select_point("select", (drone.x,drone.y))


        # construction de l'extracteur de gaz de vespene 
        extractor = self.get_units_by_type(obs,units.Zerg.Extractor)
        vespeneGeyser = self.get_units_by_type(obs,units.Neutral.VespeneGeyser)
        #print(vespeneGeyser)
        
        if len(extractor) == 0:
          if self.unit_type_is_selected(obs,units.Zerg.Drone):
            if self.can_do(obs, actions.FUNCTIONS.Build_Extractor_screen.id):
              if len(vespeneGeyser)>0:
                  return actions.FUNCTIONS.Build_Extractor_screen("now", (vespeneGeyser[0].x, vespeneGeyser[0].y))
      

        # collecte du gaz de  vespène 
        self.extractor = self.get_units_by_type(obs,units.Zerg.Extractor)
        if len(extractor) == 0:
          return actions.FUNCTIONS.no_op()
        drones = self.get_units_by_type(obs, units.Zerg.Drone)
        if len(drones) > 0 and  self.drone_selected == False:
          drone = random.choice(drones)
          self.drone_selected = True;
          return actions.FUNCTIONS.select_point("select", (drone.x,drone.y))
        if not self.gather and self.can_do(obs,actions.FUNCTIONS.Harvest_Gather_screen.id):
          self.gather = True;
          return actions.FUNCTIONS.Harvest_Gather_screen("now",(extractor[0].x,extractor[0].y))
        
          # génère une reine 
        building_type  = self.get_units_by_type(obs,units.Zerg.Hatchery)
        if len(building_type) == 0:
          return actions.FUNCTIONS.no_op()
      
        if not building_type[0].is_selected and self.queen == False:
          return actions.FUNCTIONS.select_point("select",(building_type[0].x,building_type[0].y))
  
        if mineral >= 150  and self.queen == False and self.can_do(obs, actions.FUNCTIONS.Train_Queen_quick.id):
          self.queen = True
          self.queen_count = self.queen_count + 1
          return actions.FUNCTIONS.Train_Queen_quick("now")


        # maintenant que la reine est crée, elle va injecter la Hatchery pour créer plus de larves.
        queen = self.get_units_by_type(obs, units.Zerg.Queen)
        if len(queen)>0 and queen[0].energy>=30:
          if self.queen_selected ==False :
            self.queen_selected = True
            return actions.FUNCTIONS.select_point("select", (queen[0].x,queen[0].y))
          if self.queen_selected == True :
            if self.can_do(obs, actions.FUNCTIONS.Effect_InjectLarva_screen.id):
              print(queen[0].energy)
              a=[(unit.x,unit.y) for unit in obs.observation.feature_units if unit.unit_type == 86]
              a=a[0]
              self.queen_selected=False
              return actions.FUNCTIONS.Effect_InjectLarva_screen("now",(a[0],a[1]))

        # ici on décide du nombre de reines qu'on veut. Pour créer une reine, une manière simple est de passer la variable self.queen à False
        if self.queen_count != 1: # après plusieurs tests, créer plus d'une reine n'est pas rentable car cela ralentit la production de Zerglings.
          self.queen=False

        # on mute les larves en Zerglings
        if self.unit_type_is_selected(obs, units.Zerg.Larva):
          free_supply = (obs.observation.player.food_cap - obs.observation.player.food_used)
          if free_supply == 0:
            if self.can_do(obs, actions.FUNCTIONS.Train_Overlord_quick.id):
              return actions.FUNCTIONS.Train_Overlord_quick("now")

          if self.can_do(obs, actions.FUNCTIONS.Train_Zergling_quick.id):
            return actions.FUNCTIONS.Train_Zergling_quick("now")
    
        larvae = self.get_units_by_type(obs, units.Zerg.Larva)

        if len(larvae)  == 0:
           return actions.FUNCTIONS.no_op()
        if not larvae[0].is_selected:
            return actions.FUNCTIONS.select_point("select", (larvae[0].x,larvae[0].y))
        """
        
        if larvae[0].is_selected and self.zerg == False :
          self.zerg = True 
          return actions.FUNCTIONS.Train_Zergling_quick("now")
        """


        return actions.FUNCTIONS.no_op()
