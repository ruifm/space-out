
# coding: utf-8




import math as m
import inspect
import time
import os
import sys
import numpy as np
import pygame
from pygame.locals import *

#GENERAL PARAMETERS
MAX_PLAYERS=2


#EMITTER PARAMETERS
FLAME_FRAMES=2
FLAME_RATE=10.0
SMOKE_FRAMES=2
SMOKE_TIME=0.5


# FIRING RELATED PARAMETERS
RATE_OF_FIRE=5.0  # maximum bullets per sec per player
MAX_BULLETS=10  # maximum number of simultaneous bullets on screen per player



# MOVEMENT RELATED PARAMETERS
OMEGA=0.7 # revolutions/sec
BREAK=0.8  # Ratio of backwards thrust accelaration compared to normal thrust
MAX_SPEED_R=0.4 # maximum speed in ratio of screen height per sec
DRAG_TIME=1.0 # sec until max speed is reached


BULLET_VEL_R=0.6 # bullet speed in ratio of screen height per sec in relation to the firing ship



# COLLISION RELATED PARAMETERS
INIT_COOLDOWN=3.0 # initial secs of non collision mode
COOLDOWN=1.0 #secs of non collision mode after collision
MASS_RATIO=1e-2 # m_bullet/m_ship
LOSS=0.9  # velocity loss in each collision
EXPLOSION_TIME=1.0
EXPLOSION_FRAMES=24
IMPACT_SIZE_R=0.5

# SIZE RELATED PARAMETERS (height_obj/height_screen)
SHIP_SIZE_R=0.07
BULLET_SIZE_R=SHIP_SIZE_R/5
FLAME_SIZE_R=0.12
EXPLOSION_R=3.0
SHIELD_IMG_R=1.5
SMOKE_R=0.5

BIG_FONT_R=0.08
NORMAL_FONT_R=0.06
SMALL_FONT_R=0.03

#WINDOW FRAME RATIOS
BORDER_W_R=0.03
BORDER_H_R=0.05
BORDER_BOTTOM_R=0.09

GAME_W_R=0.3
GAME_H_R=0.3


# STRINGS
WINDOW_S='SPACE OUT'
PLAYER_S='Player '
HP_S='HP: '
SCORE_S='SCORE: '
SPEED_S1='SPEED: '
SPEED_S2=''
FPS_S=' FPS'
TIME_S1='Round time: '
TIME_S2=' secs'


#FIRE CONTROLS
P1_FIRE=pygame.K_SPACE
P2_FIRE=pygame.K_1

#SOUNDS
MUSIC_VOL=0.3
MUSIC_START_TIME=20
EXPLOSION_VOL=0.1
HIT_VOL=0.05
SHOT_VOL=0.05
ENGINE_VOL=0.6
ENGINE_FADEOUT=200

#COLORS
BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)
BLUE =  (  0,   0, 255)
GREEN = (  0, 255,   0)
RED =   (255,   0,   0)


#GENERAL GEOMETRY FUNCTIONS
def norm(v):
    return np.linalg.norm(v, ord=1)

def unit(v):
    n=norm(v)
    if n==0:
        return 0
    return v/n

def VectorfromAngle(angle):
    return np.array([[np.cos(angle),-np.sin(angle)]]).reshape((2,1))


def tonumpy(v):
    return np.asarray(v,dtype=np.float32).reshape((len(v),1))





def collisionvels(obj1,obj2,App):
    v1=obj1.vel.reshape((2,))
    v2=obj2.vel.reshape((2,))
    x1=obj1.pos.reshape((2,))
    x2=obj2.pos.reshape((2,))
    m1=obj1.mass
    m2=obj2.mass
    dt=App.dt
    
    dx=norm(x1-x2)
    
    u1= ((2*m2/(m1+m2))*(np.dot(v1-v2,x1-x2)/np.dot(x1-x2,x1-x2)))
    u2= ((2*m1/(m1+m2))*(np.dot(v2-v1,x2-x1)/np.dot(x2-x1,x2-x1)))
    
    u1 = v1 - u1*(x1-x2)
    u2= v2 - u2*(x2-x1)
    
    
    obj1.vel=u1.reshape((2,1))*LOSS
    obj2.vel=u2.reshape((2,1))*LOSS
    
    obj1.last_collision=obj2
    obj2.last_collision=obj1


def collide(obj1,obj2):

    result= obj1.rect.colliderect(obj2.rect)
    if result and obj1.number!=obj2.number and obj1!=obj2:
        return True
    else:
        return False


#CLASSES

class App():
    def __init__(self,w=0,h=0,frames=60):
        pygame.init()
        self.running = True
        self.screen = None
        if w==0 and h==0:
            self.size = self.width, self.height = pygame.display.Info().current_w, pygame.display.Info().current_h
        else:
            self.size = self.width, self.height = w, h
        self.fps=frames
        self.dt=1/self.fps
        
        
    def __enter__(self):
        return self

    
    def on_init(self):
        pygame.mixer.pre_init(44100, 16, 2, 4096) #frequency, size, channels, buffersize
        pygame.init() #turn all of pygame on.
        self.screen = pygame.display.set_mode((self.width, self.height),pygame.DOUBLEBUF|pygame.HWSURFACE)
        
        self.icon=pygame.image.load('images/player1.png').convert_alpha()
        self.icon=pygame.transform.scale(self.icon, (32, 32))
        pygame.display.set_icon(self.icon)
        pygame.display.set_caption(WINDOW_S)
        
        self.flags=self.screen.get_flags()
        
        self.big_font=pygame.font.Font(None, int(BIG_FONT_R*self.height))
        self.normal_font=pygame.font.Font(None, int(NORMAL_FONT_R*self.height))
        self.small_font=pygame.font.Font(None, int(SMALL_FONT_R*self.height))

        
        self.running = True
        self.clock = pygame.time.Clock()
        
        self.players=[]
        
        
        self.all_sprites=pygame.sprite.Group()
        self.agents=pygame.sprite.Group()
        self.emitters=pygame.sprite.Group()
        self.emitters_visible=pygame.sprite.Group()
        self.explosions=pygame.sprite.Group()
        
        self.bullet_group=pygame.sprite.Group()
        
        self.playerimg=[]
        self.playerimg_shield=[]
        self.playerlogos=[]
        self.flameimg=[]
        self.smokeimg=[]
        self.explosionimg=[]
        
        self.text_player=[]
        self.text_speed=[]
        self.text_score=[]
        self.text_hp=[]
        
        self.bg=pygame.image.load("images/starfield.png").convert()
        self.bg_rect=self.bg.get_rect()
        self.bg_ar=float(self.bg_rect.width)/float(self.bg_rect.height)
        self.tile=False

        if self.bg_rect.width>self.width:
            self.bg=pygame.transform.scale(self.bg,(self.width,self.width/self.bg_ar))
        elif self.bg_rect.width>self.width:
            self.bg=pygame.transform.scale(self.bg,(self.height*self.bg_ar,self.height))
        else:
            self.tile=True

        for n in range(EXPLOSION_FRAMES):
            self.explosionimg.append(pygame.image.load("images/explosion/"+str(n+1)+'.png').convert_alpha())

        for n in range(FLAME_FRAMES):
            self.flameimg.append(pygame.image.load("images/flame"+str(n+1)+'.png').convert_alpha())

        for n in range(SMOKE_FRAMES):
            self.smokeimg.append(pygame.image.load("images/smoke"+str(n+1)+'.png').convert_alpha())


        self.sound_shot = pygame.mixer.Sound("sounds/laser_shot.wav")
        self.sound_explosion=pygame.mixer.Sound("sounds/explosion.wav")
        self.sound_hit=pygame.mixer.Sound("sounds/small_explosion.wav")
        self.sound_engine=pygame.mixer.Sound("sounds/jet.wav")



        self.sound_shot.set_volume(SHOT_VOL)
        self.sound_hit.set_volume(HIT_VOL)
        self.sound_explosion.set_volume(EXPLOSION_VOL)
        self.sound_engine.set_volume(ENGINE_VOL)


        for n in range(MAX_PLAYERS):
            self.playerimg.append(pygame.image.load("images/player"+str(n+1)+'.png').convert_alpha())
            self.playerimg_shield.append(pygame.image.load("images/player"+str(n+1)+'_shield2.png').convert_alpha())
            
            
            
            self.players.append(pygame.sprite.GroupSingle())
            
            Human(self,n,self.agents,self.players[n],self.all_sprites)
            

            
        
        self.t0=time.time()
        
        self.text_time=self.small_font.render(TIME_S1+"{:.1f}".format(time.time()-self.t0)+TIME_S2, True, WHITE)
        self.text_fps=self.small_font.render(str(int(self.clock.get_fps()))+FPS_S, True, WHITE)


            
        self.bulletimg=pygame.image.load('images/bullets.png').convert_alpha()
        
        pygame.mixer.music.set_volume(MUSIC_VOL)
        pygame.mixer.music.load('sounds/run.mp3')
        pygame.mixer.music.play(MUSIC_START_TIME)
        pygame.mixer.music.play(-1)


        
                
        
        
        
    def on_event(self, event):
        keys=pygame.key.get_pressed()
        if event.type == pygame.QUIT:
            self.running = False
        #elif event.type==VIDEORESIZE:
        #    self.screen=pygame.display.set_mode((event.w,event.h),self.flags)
        #    self.size=self.width,self.height=event.w,event.h
            
        elif event.type == pygame.KEYDOWN and keys[pygame.K_LALT] or keys[pygame.K_RALT]:
                if event.key == pygame.K_F4 and alt_pressed:
                        self.running = False
        elif event.type == pygame.KEYDOWN and (event.key==pygame.K_f or event.key==pygame.K_F10):
                if self.flags&FULLSCREEN==False:
                    self.flags|=FULLSCREEN
                    self.screen=pygame.display.set_mode(self.size, self.flags)
                else:
                    self.flags^=FULLSCREEN
                    self.screen=pygame.display.set_mode(self.size, self.flags)
        else:
            for agent in self.agents:
                agent.on_event(keys)
        
        
    def on_loop(self):
        self.PlayerHitPlayer()
        self.BulletHitPlayer()
        self.agents.update(self)
        self.bullet_group.update(self)
        self.emitters.update(self)
        self.explosions.update(self)
        
        
        self.text_time=self.small_font.render(TIME_S1+"{:.1f}".format(time.time()-self.t0)+TIME_S2, True, WHITE)
        self.text_fps=self.small_font.render(str(int(self.clock.get_fps()))+FPS_S, True, WHITE)
        
    def PlayerHitPlayer(self):
        hits=[]
        for n in range(MAX_PLAYERS):
            for p in range(MAX_PLAYERS):
                if p!=n:
                    hits.append(pygame.sprite.groupcollide(self.players[n], self.players[p], False, False,collided=pygame.sprite.collide_mask))
        for hit in hits:
            for agent,players in hit.items():
                for player in players:
                    if agent.last_collision!=player:
                        collisionvels(agent,player,self)
                        self.sound_hit.play()
                        Impact(self,agent,player,self.explosions,self.all_sprites)
                        if agent.collide:
                            agent.hp-=1
                            agent.collisiontime=time.time()
                        if player.collide:
                            player.hp-=1
                            player.collisiontime=time.time()
               
        
    def BulletHitPlayer(self):
        hits=[]
        for n in range(MAX_PLAYERS):
            for p in range(MAX_PLAYERS):
                if p!=n:
                    hits.append(pygame.sprite.groupcollide(self.players[n], self.players[p].sprites()[0].bullets, False, False,collided=pygame.sprite.collide_mask))
        for hit in hits:
            for agent, bullets in hit.items():
                for bullet in bullets:
                    if bullet not in agent.bullets:
                        if agent.last_collision!=bullet:
                            collisionvels(agent,bullet,self)
                            if agent.collide:
                                agent.hp-=1
                                agent.collisiontime=time.time()
                                Explosion(self,bullet,self.explosions,self.all_sprites)
                                bullet.kill()
                            else:
                                bullet.kill
                                bullet.add(agent.bullets,self.bullet_group,self.all_sprites)
                                bullet.number=agent.number

    def on_render(self):
            
        self.screen.fill(BLACK)

        if self.tile:
            for n in range(int(m.ceil(self.width/self.bg_rect.width))):
                for p in range(int(m.ceil(self.height/self.bg_rect.height))):
                    self.screen.blit(self.bg,(n*self.bg_rect.width,p*self.bg_rect.height))
        else:
            self.screen.blit(self.bg,(0,0))

        self.screen.blit(self.text_fps,((1-BORDER_W_R)*self.width-self.text_fps.get_width(),(1-BORDER_BOTTOM_R)*self.height-self.text_fps.get_height()))
        self.screen.blit(self.text_time,(BORDER_W_R*self.width,(1-BORDER_BOTTOM_R)*self.height-self.text_time.get_height()))
        
        for agent in self.agents:
            self.screen.blit(agent.text_player,((1-agent.number)*BORDER_W_R*self.width+agent.number*((1-BORDER_W_R)*self.width-agent.text_player.get_width()-agent.playerlogo.get_width()),BORDER_H_R*self.height))
            self.screen.blit(agent.text_hp,((1-agent.number)*BORDER_W_R*self.width+agent.number*((1-BORDER_W_R)*self.width-agent.text_hp.get_width()),BORDER_H_R*self.height+agent.text_player.get_height()))
            self.screen.blit(agent.text_score,((1-agent.number)*BORDER_W_R*self.width+agent.number*((1-BORDER_W_R)*self.width-agent.text_score.get_width()),BORDER_H_R*self.height+agent.text_player.get_height()+agent.text_hp.get_height())) 
            self.screen.blit(agent.text_speed,((1-agent.number)*BORDER_W_R*self.width+agent.number*((1-BORDER_W_R)*self.width-agent.text_speed.get_width()),BORDER_H_R*self.height+agent.text_player.get_height()+agent.text_hp.get_height()+agent.text_score.get_height())) 
            self.screen.blit(agent.playerlogo,((1-agent.number)*(BORDER_W_R*self.width+agent.text_player.get_width())+agent.number*((1-BORDER_W_R)*self.width-agent.playerlogo.get_width()),BORDER_H_R*self.height))



        self.bullet_group.draw(self.screen)
        self.emitters_visible.draw(self.screen)
        self.agents.draw(self.screen)
        self.explosions.draw(self.screen)
        
        
        pygame.display.flip()
        self.clock.tick(self.fps)

    def restart(self):
        self.t0=time.time()
        for agent in self.agents:
            agent.on_init(self)

    def on_cleanup(self):
        pygame.quit()
 
    def on_execute(self):
        if self.on_init() == False:
            self.running = False
      
        while( self.running ):
            for event in pygame.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()
        self.on_cleanup()
    def __exit__(self,exc_type, exc_value, traceback):
        pygame.quit()





class Human(pygame.sprite.Sprite):
    def __init__(self,App,n,*sprite_groups):
        super().__init__(*sprite_groups)
        self.number=n
        self.mass=1
        self.score=-1
        self.MAX_SPEED=App.height*MAX_SPEED_R
        self.THRUST_V=self.MAX_SPEED/DRAG_TIME        
        self.controls=Control(self)
        self.bullets=pygame.sprite.Group()

        self.on_init(App)
            
    def on_init(self,App):
        self.dead=False
        self.score+=1
        self.pos=np.array([np.random.random_sample()*App.width*(1-2*GAME_W_R)+GAME_W_R*App.width,np.random.random_sample()*App.height*(1-2*GAME_H_R)+GAME_H_R*App.height]).reshape((2,1))
        self.wrap(App)
        self.vel=np.zeros((2,1))
        self.accel=np.zeros((2,1))
        self.angle=np.random.random_sample()*(2*np.pi)
        self.rot=0
        self.hp=3
        self.thrust=0
        self.fire=False
        self.last_fire=time.time()
        self.collide=False
        self.collide_prev=self.collide
        self.collisiontime=time.time()
        self.last_collision=self
        

        self.text_player=App.big_font.render(PLAYER_S, True, WHITE)
        self.text_speed=App.small_font.render(SPEED_S1+"{:3.1f}".format(norm(self.vel)*100/(self.MAX_SPEED))+SPEED_S2, True, WHITE)
        self.text_score=App.normal_font.render(SCORE_S+str(self.score), True, WHITE)
        self.text_hp=App.normal_font.render(HP_S+str(self.hp), True, WHITE)
        self.playerlogo=pygame.transform.scale(App.playerimg[self.number],(int(App.playerimg[self.number].get_width()*self.text_player.get_height()/App.playerimg[self.number].get_height()),int(self.text_player.get_height())))


        self.emitter=Emitter(self,App,App.emitters,App.all_sprites)


        self.original=App.playerimg[self.number]
        self.original_shield=App.playerimg_shield[self.number]
        self.aspect_ratio=float(self.original.get_width())/float(self.original.get_height())
        self.scale=SHIP_SIZE_R
        
        
        self.resize(App)
        self.load_rot()
        self.rect=self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)    
        
    def resize(self,App):
        self.original=pygame.transform.smoothscale(self.original,(int(self.aspect_ratio*self.scale*App.height),int(self.scale*App.height)))
        self.original_shield=pygame.transform.smoothscale(self.original_shield,(int(SHIELD_IMG_R*self.aspect_ratio*self.scale*App.height),int(SHIELD_IMG_R*self.scale*App.height)))
        self.mask_orig = pygame.mask.from_surface(self.original)
        if self.collide:
            self.image=self.original
        else:
            self.image=self.original_shield
        self.rect=self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        
    def move(self):
        self.rect.move_ip(tuple(self.pos-tonumpy(self.rect.center)))
        
        
    def rotate(self,angle,orig):
        old=self.rect.center
        self.image = pygame.transform.rotate(orig, m.degrees(angle))
        self.rect=self.image.get_rect(center=old)
        self.mask = pygame.mask.from_surface(self.image)
    
    def load_rot(self):
        if self.collide:
            self.rotate(self.angle,self.original)
        else:
            self.rotate(self.angle,self.original_shield)
        
    
    def on_event(self, keys):
        if keys[self.controls.left] and keys[self.controls.right]:
            self.rot=0
        elif keys[self.controls.left]:
            self.rot=OMEGA
        elif keys[self.controls.right]:
            self.rot=-OMEGA
        else: self.rot=0
        
        if keys[self.controls.up] and keys[self.controls.down]:
            self.thrust=0
        elif keys[self.controls.up]:
            self.thrust=self.THRUST_V
        elif keys[self.controls.down]:
            self.thrust=-BREAK*self.THRUST_V
        else:
            self.thrust=0
        
        if keys[self.controls.fire]:
            self.fire=True
        else:
            self.fire=False


    def shoot(self,App):
        now=time.time()
        if len(self.bullets)<=MAX_BULLETS and now-self.last_fire>=1./RATE_OF_FIRE and self.collide:
            self.last_fire=now
            App.sound_shot.play()
            Bullet(self,App,App.bullet_group,self.bullets,App.all_sprites)

    def wrap(self,App):
        b=np.array([[App.width+1.0,App.height+1.0]]).reshape((2,1))
        self.pos=np.remainder(self.pos,b)
        
        
        
    def update(self,App):
        self.angle+=App.dt*self.rot*2*m.pi
        
        self.accel=VectorfromAngle(self.angle)*self.thrust
               
        self.vel+=App.dt*(self.accel-self.vel/DRAG_TIME)
        if norm(self.vel)> self.MAX_SPEED:
            self.vel=unit(self.vel)*self.MAX_SPEED
        
        self.pos+=App.dt*self.vel
        self.wrap(App)
        
        
        
        if self.fire:
            self.shoot(App)
        
        if self.thrust>0:
            self.emitter.visible=True
        else:
            self.emitter.visible=False

        if time.time()-App.t0 > INIT_COOLDOWN and time.time()-self.collisiontime> COOLDOWN:
            self.collide_prev=self.collide
            self.collide=True
            
        else:
            self.collide_prev=self.collide
            self.collide=False
            
        if self.emitter.visible or self.emitter.smoke:
            self.emitter.pos=self.pos-VectorfromAngle(self.angle)*self.mask_orig.get_size()[0]
            self.emitter.angle=self.angle
        
        
        
        if not collide(self,self.last_collision):
            self.last_collision=self
        
        if self.hp<=0:
            if not self.dead:
                self.die(App)


        
        self.text_speed=App.small_font.render(SPEED_S1+"{:3.1f}".format(norm(self.vel)*100/(self.MAX_SPEED))+SPEED_S2, True, WHITE)
        self.text_score=App.normal_font.render(SCORE_S+str(self.score), True, WHITE)
        self.text_hp=App.normal_font.render(HP_S+str(self.hp), True, WHITE)
        

        self.on_render(App)
        
    def on_render(self,App):
        if self.collide!=self.collide_prev or self.rot!=0:
            self.load_rot()
        self.move()



    def die(self,App):
        self.dead=True
        self.score-=1
        Explosion(App,self,App.explosions,App.all_sprites)
        
    

class Control():
    def __init__(self,Human):
        if Human.number==0:
            self.left=pygame.K_LEFT
            self.right=pygame.K_RIGHT
            self.up=pygame.K_UP
            self.down=pygame.K_DOWN
            self.fire=P1_FIRE
        elif Human.number==1:
            self.left=pygame.K_a
            self.right=pygame.K_d
            self.up=pygame.K_w
            self.down=pygame.K_s
            self.fire=P2_FIRE
        else:
            print('ERROR: MAX_PLAYERS>2, please define more controls')
    


class Bullet(pygame.sprite.Sprite):
    def __init__(self,Human,App,*sprite_groups):
        super().__init__(*sprite_groups)
        self.BULLET_VEL=App.height*BULLET_VEL_R
        self.angle=Human.angle
        self.pos=Human.pos
        self.vel=Human.vel+VectorfromAngle(self.angle)*self.BULLET_VEL
        self.mass=Human.mass*MASS_RATIO
        self.collisiontime=time.time()
        self.last_collision=self
        self.number=Human.number
        
        self.scale=BULLET_SIZE_R
        
        Human.vel-=MASS_RATIO*self.vel
        
        self.load(App)
    
    
    def resize(self,App):
        self.original=pygame.transform.smoothscale(self.original,(int(self.aspect_ratio*self.scale*App.height),int(self.scale*App.height)))
        self.image = self.original
        self.rect=self.image.get_rect()
        
    def move(self):
        self.rect.move_ip(tuple(self.pos-tonumpy(self.rect.center)))
        
        
    def rotate(self,angle):
        old=self.rect.center
        self.image = pygame.transform.rotate(self.original, m.degrees(angle))
        self.rect=self.image.get_rect(center=old)
        self.mask = pygame.mask.from_surface(self.image)
    
    
    def load(self,App):
        self.original=App.bulletimg
        self.aspect_ratio=float(self.original.get_width())/float(self.original.get_height())
        
        
        self.resize(App)
        self.rotate(self.angle)
        self.move()
        
    def update(self,App):
               
        self.pos+=App.dt*self.vel
        
        if  self.pos[0]>App.width or self.pos[0]<0 or self.pos[1]>App.height or self.pos[1]<0:
            self.kill()
        
        
        if not collide(self,self.last_collision):
            self.last_collision=self


        self.on_render(App)

    def on_render(self,App):
        self.move()


class Emitter(pygame.sprite.Sprite):
    def __init__(self,Human,App,*sprite_groups):
        super().__init__(*sprite_groups)
        self.number=Human.number
        self.frame=0
        self.angle=Human.angle
        self.pos=Human.pos#-VectorfromAngle(self.angle)*App.agents.sprites()[self.number].original.get_width()
        

        self.tpf=1.0/(FLAME_FRAMES*FLAME_RATE)

        self.time_of_frame=time.time()
        self.timer=time.time()

        self.visible=False
        self.visible_prev=False
        self.smoke=False


        self.sound=App.sound_engine
        
        self.scale=FLAME_SIZE_R
        self.scale_smoke=self.scale*SMOKE_R
        self.original=App.flameimg
        self.original_smoke=App.smokeimg
        self.aspect_ratio=[]
        self.aspect_ratio_smoke=[]

        for n in range(len(App.flameimg)):
            self.aspect_ratio.append(float(self.original[n].get_width())/float(self.original[n].get_height()))

        for n in range(len(App.smokeimg)):
            self.aspect_ratio_smoke.append(float(self.original_smoke[n].get_width())/float(self.original_smoke[n].get_height()))
        
        self.resize(App)
        self.load(App)
        
    
    def resize(self,App):
        for n in range(len(self.original)):
            self.original[n]=pygame.transform.smoothscale(self.original[n],(int(self.aspect_ratio[n]*self.scale*App.height),int(self.scale*App.height)))
        for n in range(len(self.original_smoke)):
            self.original_smoke[n]=pygame.transform.smoothscale(self.original_smoke[n],(int(self.aspect_ratio_smoke[n]*self.scale_smoke*App.height),int(self.scale_smoke*App.height)))
        
    def move(self):
        self.rect.move_ip(tuple(self.pos-tonumpy(self.rect.center)))
        
        
    def rotate(self,angle):
        if self.smoke:
            self.image=pygame.transform.rotate(self.original_smoke[self.frame%FLAME_FRAMES], m.degrees(angle))
        elif self.visible:
            self.image=pygame.transform.rotate(self.original[self.frame%FLAME_FRAMES], m.degrees(angle))
        else:
            self.image=pygame.transform.rotate(self.original[self.frame%FLAME_FRAMES], m.degrees(angle))
        
        self.rect=self.image.get_rect()
        
    
    
    def load(self,App):
        
        self.rotate(self.angle)
        if self.smoke:
            self.rect.move_ip(tuple(self.pos-tonumpy(self.rect.center)+VectorfromAngle(self.angle)*self.rect.width/3))
        else:
            self.move()
        
    def update(self,App):
        if self.visible or self.smoke:
            now=time.time()
            if now-self.time_of_frame>=self.tpf:
                self.frame+=1
                self.time_of_frame=now
            
            if self.smoke:
                if now-self.timer > SMOKE_TIME:
                    self.smoke=False


        if self.visible_prev!=self.visible:
            if self.visible:
                self.sound.play(-1)
            else:
                self.timer=time.time()
                self.smoke=True
                self.sound.fadeout(ENGINE_FADEOUT)



        self.visible_prev=self.visible
        self.on_render(App)
        
    def on_render(self,App):
        self.load(App)

        if self.visible or self.smoke:
            self.add(App.emitters_visible)
        else:
            self.remove(App.emitters_visible)


class Explosion(pygame.sprite.Sprite):
    def __init__(self,App,obj,*sprite_groups):
        super().__init__(*sprite_groups)
        
        self.pos=obj.pos
        

        self.frame=0
        
        self.scale=obj.scale*EXPLOSION_R
        

        self.tpf=EXPLOSION_TIME/EXPLOSION_FRAMES

        self.time_of_frame=time.time()

        if isinstance(obj,Human):
            self.restart=True
        else:
            self.restart=False
        
        self.exists=True

        if isinstance(obj,Bullet):
            App.sound_hit.play()
        else:
            App.sound_explosion.play()

        self.load(App)
    
    
    def resize(self,App):
        self.original=pygame.transform.smoothscale(self.original,(int(self.aspect_ratio*self.scale*App.height),int(self.scale*App.height)))
        self.image=self.original
        self.rect=self.image.get_rect()
        
    def move(self):
        self.rect.move_ip(tuple(self.pos-tonumpy(self.rect.center)))
        
    def load(self,App):
         
        self.original=App.explosionimg[self.frame]
        self.aspect_ratio=float(self.original.get_width())/float(self.original.get_height())
        
        
        self.resize(App)
        
        self.move()
        


    def update(self,App):
        if self.exists:
            self.load(App)
            now=time.time()
            if now-self.time_of_frame>=self.tpf:
                self.frame+=1
                self.time_of_frame=now
            if self.frame>=EXPLOSION_FRAMES-1:
                self.kill()
                if self.restart:
                    App.restart()
                    self.exists=False


class Impact(pygame.sprite.Sprite):
    def __init__(self,App,obj1,obj2,*sprite_groups):
        super().__init__(*sprite_groups)
        
        self.pos=obj1.pos/2+obj2.pos/2
        

        self.frame=0
        
        self.scale=(obj2.scale+obj1.scale)*IMPACT_SIZE_R/2
        

        self.tpf=EXPLOSION_TIME/EXPLOSION_FRAMES

        self.time_of_frame=time.time()


        
        App.sound_hit.play()
        

        self.load(App)
    
    
    def resize(self,App):
        self.original=pygame.transform.smoothscale(self.original,(int(self.aspect_ratio*self.scale*App.height),int(self.scale*App.height)))
        self.image=self.original
        self.rect=self.image.get_rect()
        
    def move(self):
        self.rect.move_ip(tuple(self.pos-tonumpy(self.rect.center)))
        
    def load(self,App):
         
        self.original=App.explosionimg[self.frame]
        self.aspect_ratio=float(self.original.get_width())/float(self.original.get_height())
        
        
        self.resize(App)
        
        self.move()
        


    def update(self,App):
        self.load(App)
        now=time.time()
        if now-self.time_of_frame>=self.tpf:
            self.frame+=1
            self.time_of_frame=now
        if self.frame>=EXPLOSION_FRAMES-1:
            self.kill()
        

        










if __name__ == "__main__" :
    with App() as theApp:
        theApp.on_execute()
        


