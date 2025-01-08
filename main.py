from settings import *
from game_data import *
from pytmx.util_pygame import load_pygame
from sprites import Sprite,AnimatedSprite,BorderSprite,CollidableSprite,TransitionSprite
from entities import Player,Character
from groups import AllSprites
from support import *
from os.path import join
from dialog import DialogTree

class Game:
    def __init__(self):
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH,WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()


        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.character_sprites = pygame.sprite.Group()
        self.transition_sprites = pygame.sprite.Group()

        self.transition_target = None
        self.tint_surf = pygame.Surface((WINDOW_WIDTH,WINDOW_HEIGHT))
        self.tint_mode = 'untint'
        self.tint_progress = 0
        self.tint_direction = -1
        self.tint_speed = 600

        self.import_assests()
        self.setup(self.tmx_maps['world'],'house')
        self.dialog_tree = None

    def import_assests(self):
        self.tmx_maps = tmx_importer('data','maps')

        self.overworld_frames = {
            'water':import_folder('graphics','tilesets','water'),
            'coast': coast_importer(24,12,'graphics','tilesets','coast'),
            'characters': all_character_import('graphics','characters')
            }
        
        self.fonts = {
            'dialog': pygame.font.Font(join('graphics','fonts','PixeloidSans.ttf'),30),
            'intro': pygame.font.Font(join('graphics','fonts','PixeloidSans.ttf'),50)
        }

    def intro_screen(self):
        running = True
        font = self.fonts['intro']
        while running:
            self.display_surface.fill(COLORS['black'])  

            
            title_text = font.render("Test", True, (255, 255, 255))
            title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, 150))
            self.display_surface.blit(title_text, title_rect)

            
            mouse_pos = pygame.mouse.get_pos()
            start_button = pygame.Rect(WINDOW_WIDTH // 2 - 100, 300, 200, 60)
            quit_button = pygame.Rect(WINDOW_WIDTH // 2 - 100, 400, 200, 60)

            # Kiểm tra con chuột
            pygame.draw.rect(self.display_surface, (0, 102, 204) if start_button.collidepoint(mouse_pos) else (150, 150, 150), start_button)
            pygame.draw.rect(self.display_surface, (0, 102, 204) if quit_button.collidepoint(mouse_pos) else (150, 150, 150), quit_button)

            # Hiển thị text của nút
            start_text = font.render("Start", True, (255, 255, 255))
            quit_text = font.render("Quit", True, (255, 255, 255))
            self.display_surface.blit(start_text, start_text.get_rect(center=start_button.center))
            self.display_surface.blit(quit_text, quit_text.get_rect(center=quit_button.center))

            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if start_button.collidepoint(event.pos):
                        running = False  
                    elif quit_button.collidepoint(event.pos):
                        pygame.quit()
                        exit()

            pygame.display.update()
            self.clock.tick(60)

    def setup(self,tmx_map,player_start_pos):
        for group in (self.all_sprites,self.collision_sprites,self.transition_sprites,self.character_sprites):
            group.empty()

        for layer in ['Terrain','Terrain Top']:
            for x,y,surf in tmx_map.get_layer_by_name(layer).tiles():
                Sprite((x * TILE_SIZE, y * TILE_SIZE),surf,self.all_sprites,WORLD_LAYERS['bg'])
        
        for obj in tmx_map.get_layer_by_name('Water'):
            for x in range(int(obj.x),int(obj.x + obj.width),TILE_SIZE):
                for y in range(int(obj.y),int(obj.y + obj.height), TILE_SIZE):
                    AnimatedSprite((x,y),self.overworld_frames['water'],self.all_sprites,WORLD_LAYERS['water'])

        for obj in tmx_map.get_layer_by_name('Coast'):
            terrain = obj.properties['terrain']
            side = obj.properties['side']
            AnimatedSprite((obj.x,obj.y),self.overworld_frames['coast'][terrain][side],self.all_sprites,WORLD_LAYERS['bg'])

        for obj in tmx_map.get_layer_by_name('Objects'):
            if obj.name == 'top':
                Sprite((obj.x,obj.y),obj.image,self.all_sprites,WORLD_LAYERS['top'])
            else:
                CollidableSprite((obj.x,obj.y),obj.image,(self.all_sprites,self.collision_sprites))

        for obj in tmx_map.get_layer_by_name('Transition'):
            TransitionSprite((obj.x,obj.y),(obj.width,obj.height),(obj.properties['target'],obj.properties['pos']),self.transition_sprites)

        for obj in tmx_map.get_layer_by_name('Collisions'):
            BorderSprite((obj.x,obj.y),pygame.Surface((obj.width,obj.height)),self.collision_sprites)

        for obj in tmx_map.get_layer_by_name('Entities'):
            if obj.name == 'Player' and obj.properties['pos'] == player_start_pos:
                self.player = Player(
                    pos = (obj.x,obj.y),
                    frames = self.overworld_frames['characters']['player'],
                    groups = self.all_sprites,
                    facing_direction = obj.properties['direction'],
                    collision_sprites = self.collision_sprites)
            elif obj.name == 'Character': 
                Character(
                    pos = (obj.x,obj.y),
                    frames = self.overworld_frames['characters'][obj.properties['graphic']],
                    groups = (self.all_sprites,self.collision_sprites,self.character_sprites),
                    facing_direction = obj.properties['direction'],
                    character_data = TRAINER_DATA[obj.properties['character_id']]
                )
        
    def input(self):
        if not self.dialog_tree:
            key = pygame.key.get_pressed()
            if key[pygame.K_e]:
                for character in self.character_sprites:
                    if check_connection(100,self.player,character):
                        self.player.block()
                        character.change_facing_direction(self.player.rect.center)
                        self.create_dialog(character)

    def create_dialog(self,character):
        if not self.dialog_tree:
            self.dialog_tree = DialogTree(character,self.player,self.all_sprites,self.fonts['dialog'],self.end_dialog)

    def end_dialog(self,character):
        self.dialog_tree = None
        self.player.unblock()

			
    def transition_check(self):
        sprites = [sprite for sprite in self.transition_sprites if sprite.rect.colliderect(self.player.hitbox)]
        key = pygame.key.get_pressed()
        if sprites:
            self.player.block()
            # self.transition_box()
            if key[pygame.K_y]:
                self.transition_target = sprites[0].target
                self.tint_mode = 'tint'
            elif key[pygame.K_UP] or key[pygame.K_DOWN] or key[pygame.K_LEFT] or key[pygame.K_RIGHT] :
                self.player.unblock()

    def tint_screen(self,dt):
        if self.tint_mode == 'untint':
            self.tint_progress -= self.tint_speed * dt
        
        if self.tint_mode == 'tint':
            self.tint_progress += self.tint_speed * dt
            if self.tint_progress >= 255:
                self.setup(self.tmx_maps[self.transition_target[0]],self.transition_target[1])
                self.tint_mode = 'untint'
                self.transition_target = None

        self.tint_progress = max(0, min(self.tint_progress, 255))
        self.tint_surf.set_alpha(self.tint_progress)
        self.display_surface.blit(self.tint_surf,(0,0))
    
    def run(self):
        self.intro_screen()

        while True:
            dt = self.clock.tick() / 1000
            self.display_surface.fill('black')
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

            #Cập nhật
            self.input()
            self.transition_check()
            self.all_sprites.update(dt)
            self.all_sprites.draw(self.player.rect.center)
            
            self.tint_screen(dt)

            if self.dialog_tree: self.dialog_tree.update()

            pygame.display.update()

if __name__ == '__main__':
    game = Game()
    game.run()
