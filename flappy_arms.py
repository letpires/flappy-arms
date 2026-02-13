import pygame
import cv2
import mediapipe as mp
import random
import sys

# Inicializar Pygame
pygame.init()

try:
    logo_image = pygame.image.load("logo_image.png")

    logo_image = pygame.transform.scale(logo_image, (200, 200))

except:
    logo_image = None


# Configurações da tela
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Gym Flappy Bird")

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (135, 206, 250)
GREEN = (34, 139, 34)
YELLOW = (255, 215, 0)
RED = (220, 20, 60)

# Configurações do jogo
GRAVITY = 0.5
FLAP_STRENGTH = -10
PIPE_WIDTH = 70
PIPE_GAP = 200
PIPE_SPEED = 3
BIRD_SIZE = 40

# FPS
clock = pygame.time.Clock()
FPS = 60

# Fontes
font_small = pygame.font.Font(None, 36)
font_large = pygame.font.Font(None, 72)
font_medium = pygame.font.Font(None, 48)

class Bird:
    def __init__(self):
        self.x = 100
        self.y = SCREEN_HEIGHT // 2
        self.velocity = 0
        self.size = BIRD_SIZE
        
    def flap(self):
        self.velocity = FLAP_STRENGTH
        
    def update(self):
        self.velocity += GRAVITY
        self.y += self.velocity
        
        # Limites da tela
        if self.y < 0:
            self.y = 0
            self.velocity = 0
        if self.y > SCREEN_HEIGHT - self.size:
            self.y = SCREEN_HEIGHT - self.size
            self.velocity = 0
            
    def draw(self, screen):
        # Desenhar pássaro (círculo amarelo com olho)
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.size // 2)
        # Olho
        pygame.draw.circle(screen, BLACK, (int(self.x + 10), int(self.y - 5)), 5)
        # Bico
        pygame.draw.polygon(screen, RED, [
            (self.x + self.size // 2, self.y),
            (self.x + self.size // 2 + 15, self.y - 5),
            (self.x + self.size // 2 + 15, self.y + 5)
        ])
        
    def get_rect(self):
        return pygame.Rect(self.x - self.size // 2, self.y - self.size // 2, self.size, self.size)

class Pipe:
    def __init__(self, x):
        self.x = x
        self.gap_y = random.randint(150, SCREEN_HEIGHT - PIPE_GAP - 150)
        self.width = PIPE_WIDTH
        self.scored = False
        
    def update(self):
        self.x -= PIPE_SPEED
        
    def draw(self, screen):
        # Cano superior
        pygame.draw.rect(screen, GREEN, (self.x, 0, self.width, self.gap_y))
        pygame.draw.rect(screen, (0, 100, 0), (self.x, 0, self.width, self.gap_y), 3)
        
        # Cano inferior
        pygame.draw.rect(screen, GREEN, (self.x, self.gap_y + PIPE_GAP, self.width, SCREEN_HEIGHT))
        pygame.draw.rect(screen, (0, 100, 0), (self.x, self.gap_y + PIPE_GAP, self.width, SCREEN_HEIGHT), 3)
        
    def collides_with(self, bird):
        bird_rect = bird.get_rect()
        
        # Cano superior
        top_pipe = pygame.Rect(self.x, 0, self.width, self.gap_y)
        # Cano inferior
        bottom_pipe = pygame.Rect(self.x, self.gap_y + PIPE_GAP, self.width, SCREEN_HEIGHT)
        
        return bird_rect.colliderect(top_pipe) or bird_rect.colliderect(bottom_pipe)
    
    def is_off_screen(self):
        return self.x < -self.width

class PoseDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.cap = cv2.VideoCapture(0)
        self.baseline_shoulder_y = None
        self.calibrated = False
        self.arms_raised = False
        self.last_raised = False
        
    def calibrate(self):
        """Calibra a posição inicial dos ombros"""
        ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)
            
            if results.pose_landmarks:
                # Pegar posição Y dos ombros
                left_shoulder = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                right_shoulder = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                
                self.baseline_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
                self.calibrated = True
                return True
        return False
    
    def detect_arms_raised(self):
        """Detecta se os braços estão levantados"""
        ret, frame = self.cap.read()
        if not ret:
            return False, None
            
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)
        
        if results.pose_landmarks and self.calibrated:
            # Pegar posição dos pulsos e ombros
            left_wrist = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_WRIST]
            right_wrist = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_WRIST]
            left_shoulder = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
            right_shoulder = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
            
            # Verificar se os pulsos estão acima dos ombros
            left_raised = left_wrist.y < left_shoulder.y - 0.1
            right_raised = right_wrist.y < right_shoulder.y - 0.1
            
            # Detectar apenas a transição de não-levantado para levantado
            currently_raised = left_raised or right_raised
            flap_triggered = currently_raised and not self.last_raised
            
            self.last_raised = currently_raised
            self.arms_raised = currently_raised
            
            return flap_triggered, cv2.flip(frame, 1)
        
        return False, cv2.flip(frame, 1) if ret else None
    
    def release(self):
        self.cap.release()

def draw_text(text, font, color, x, y, center=False):
    """Desenha texto na tela"""
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    screen.blit(text_surface, text_rect)

def draw_camera_feed(frame, x, y, width, height):
    """Desenha o feed da câmera na tela do Pygame"""
    if frame is not None:
        frame_small = cv2.resize(frame, (width, height))
        frame_rgb = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
        screen.blit(frame_surface, (x, y))

def menu_screen(pose_detector):
    """Tela de menu inicial"""
    waiting = True
    calibrating = False
    
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    calibrating = True
                    if pose_detector.calibrate():
                        return "play"
                if event.key == pygame.K_SPACE and pose_detector.calibrated:
                    return "play"
                if event.key == pygame.K_ESCAPE:
                    return "quit"
        
        # Pegar frame da câmera
        _, frame = pose_detector.cap.read()
        if frame is not None:
            frame = cv2.flip(frame, 1)
        
        screen.fill(BLUE)
        

        if logo_image:
            logo_x = SCREEN_WIDTH // 2 - 100
            logo_y = 10
            screen.blit(logo_image, (logo_x, logo_y))
        
        # Título
        draw_text("GYM FLAPPY BIRD", font_medium, WHITE, SCREEN_WIDTH // 2, 200, center=True)
        
        # Instruções
        y_pos = 250
        if not pose_detector.calibrated:
            draw_text("Pressione C para CALIBRAR", font_small, WHITE, SCREEN_WIDTH // 2, y_pos, center=True)
            if calibrating:
                draw_text("Calibrando...", font_small, YELLOW, SCREEN_WIDTH // 2, y_pos + 40, center=True)
        else:
            draw_text("CALIBRADO!", font_small, GREEN, SCREEN_WIDTH // 2, y_pos, center=True)
            draw_text("Pressione ESPAÇO para JOGAR", font_small, WHITE, SCREEN_WIDTH // 2, y_pos + 50, center=True)
        
        cam_width = 400   # largura da câmera
        cam_height = 250  # altura da câmera
        draw_camera_feed(frame, (SCREEN_WIDTH - cam_width) // 2, (SCREEN_HEIGHT - cam_height) // 2, cam_width, cam_height)
        
        # Instruções
        draw_text("Levante os braços para voar!", font_small, BLACK, SCREEN_WIDTH // 2, 560, center=True)
        
        pygame.display.flip()
        clock.tick(30)
    
    return "quit"

def game_over_screen(score, high_score):
    """Tela de game over"""
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return "play"
                if event.key == pygame.K_ESCAPE:
                    return "menu"
        
        screen.fill(BLUE)
        
        draw_text("GAME OVER!", font_large, RED, SCREEN_WIDTH // 2, 150, center=True)
        draw_text(f"Pontuação: {score}", font_medium, WHITE, SCREEN_WIDTH // 2, 250, center=True)
        draw_text(f"Recorde: {high_score}", font_medium, YELLOW, SCREEN_WIDTH // 2, 320, center=True)
        draw_text("ESPAÇO - Jogar Novamente", font_small, WHITE, SCREEN_WIDTH // 2, 420, center=True)
        draw_text("ESC - Menu", font_small, WHITE, SCREEN_WIDTH // 2, 470, center=True)
        
        pygame.display.flip()
        clock.tick(30)
    
    return "quit"

def main():
    """Loop principal do jogo"""
    pose_detector = PoseDetector()
    high_score = 0
    
    state = "menu"
    
    try:
        while True:
            if state == "menu":
                state = menu_screen(pose_detector)
                if state == "quit":
                    break
                    
            elif state == "play":
                # Inicializar jogo
                bird = Bird()
                pipes = [Pipe(SCREEN_WIDTH + 200)]
                score = 0
                running = True
                
                while running:
                    # Eventos
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                            state = "quit"
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                running = False
                                state = "menu"
                    
                    # Detectar braços levantados
                    flap_triggered, camera_frame = pose_detector.detect_arms_raised()
                    if flap_triggered:
                        bird.flap()
                    
                    # Atualizar pássaro
                    bird.update()
                    
                    # Atualizar canos
                    for pipe in pipes:
                        pipe.update()
                        
                        # Verificar colisão
                        if pipe.collides_with(bird):
                            running = False
                            if score > high_score:
                                high_score = score
                            state = "game_over"
                        
                        # Pontuar
                        if not pipe.scored and pipe.x + pipe.width < bird.x:
                            pipe.scored = True
                            score += 1
                    
                    # Remover canos fora da tela
                    pipes = [p for p in pipes if not p.is_off_screen()]
                    
                    # Adicionar novos canos
                    if len(pipes) == 0 or pipes[-1].x < SCREEN_WIDTH - 300:
                        pipes.append(Pipe(SCREEN_WIDTH))
                    
                    # Verificar se o pássaro saiu da tela
                    if bird.y >= SCREEN_HEIGHT - bird.size or bird.y <= 0:
                        running = False
                        if score > high_score:
                            high_score = score
                        state = "game_over"
                    
                    # Desenhar
                    screen.fill(BLUE)
                    
                    # Desenhar nuvens
                    for i in range(3):
                        pygame.draw.ellipse(screen, WHITE, (50 + i * 150, 50 + i * 80, 80, 40))
                    
                    # Desenhar canos
                    for pipe in pipes:
                        pipe.draw(screen)
                    
                    # Desenhar pássaro
                    bird.draw(screen)
                    
                    # Desenhar pontuação
                    draw_text(f"Score: {score}", font_medium, WHITE, 10, 10)
                    
                    # Desenhar feed da câmera (pequeno no canto)
                    if camera_frame is not None:
                        draw_camera_feed(camera_frame, 250, 10, 140, 105)
                    
                    # Indicador de braços levantados
                    if pose_detector.arms_raised:
                        draw_text("BRAÇOS UP!", font_small, GREEN, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30, center=True)
                    
                    pygame.display.flip()
                    clock.tick(FPS)
            
            elif state == "game_over":
                state = game_over_screen(score, high_score)
                if state == "quit":
                    break
            
            else:
                break
    
    finally:
        pose_detector.release()
        pygame.quit()

if __name__ == "__main__":
    main()