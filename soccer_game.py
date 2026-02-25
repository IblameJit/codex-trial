"""Arcade-style 2D soccer game using pygame.

Run:
    python soccer_game.py
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame
from pygame.math import Vector2


WIDTH, HEIGHT = 1000, 620
FPS = 60

GRASS = (34, 139, 34)
WHITE = (245, 245, 245)
BLUE = (65, 120, 230)
RED = (220, 70, 70)
BLACK = (15, 15, 15)
YELLOW = (255, 214, 10)


@dataclass
class Goal:
    x: float
    y: float
    width: float
    height: float

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), int(self.width), int(self.height))


class Player:
    def __init__(self, pos: tuple[float, float], color: tuple[int, int, int], controls: dict[int, Vector2]):
        self.pos = Vector2(pos)
        self.vel = Vector2(0, 0)
        self.color = color
        self.controls = controls
        self.radius = 20
        self.max_speed = 5.2
        self.accel = 0.68
        self.friction = 0.84

    def update(self, pressed: pygame.key.ScancodeWrapper) -> None:
        direction = Vector2(0, 0)
        for key, vec in self.controls.items():
            if pressed[key]:
                direction += vec

        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.vel += direction * self.accel

        if self.vel.length() > self.max_speed:
            self.vel.scale_to_length(self.max_speed)

        self.vel *= self.friction
        self.pos += self.vel

        self.pos.x = max(self.radius, min(WIDTH - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(HEIGHT - self.radius, self.pos.y))

    def kick(self, ball: "Ball") -> None:
        offset = ball.pos - self.pos
        min_dist = self.radius + ball.radius
        if offset.length_squared() == 0:
            offset = Vector2(random.uniform(-1, 1), random.uniform(-1, 1))

        dist = offset.length()
        if dist <= min_dist + 14:
            direction = offset.normalize()
            ball.vel += direction * 4.8

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.circle(screen, BLACK, self.pos, self.radius + 2)
        pygame.draw.circle(screen, self.color, self.pos, self.radius)


class Ball:
    def __init__(self, pos: tuple[float, float]):
        self.pos = Vector2(pos)
        self.vel = Vector2(0, 0)
        self.radius = 12
        self.drag = 0.985
        self.max_speed = 9.5

    def reset(self) -> None:
        self.pos = Vector2(WIDTH / 2, HEIGHT / 2)
        angle = random.uniform(0, math.tau)
        self.vel = Vector2(math.cos(angle), math.sin(angle)) * random.uniform(2.0, 3.2)

    def update(self, left_goal: Goal, right_goal: Goal) -> None:
        if self.vel.length() > self.max_speed:
            self.vel.scale_to_length(self.max_speed)

        self.pos += self.vel
        self.vel *= self.drag

        # Bounce off top/bottom walls.
        if self.pos.y < self.radius:
            self.pos.y = self.radius
            self.vel.y *= -0.9
        elif self.pos.y > HEIGHT - self.radius:
            self.pos.y = HEIGHT - self.radius
            self.vel.y *= -0.9

        # Bounce off side walls unless entering goal opening.
        in_left_goal_opening = left_goal.y < self.pos.y < left_goal.y + left_goal.height
        in_right_goal_opening = right_goal.y < self.pos.y < right_goal.y + right_goal.height

        if self.pos.x < self.radius and not in_left_goal_opening:
            self.pos.x = self.radius
            self.vel.x *= -0.92
        elif self.pos.x > WIDTH - self.radius and not in_right_goal_opening:
            self.pos.x = WIDTH - self.radius
            self.vel.x *= -0.92

    def resolve_player_collision(self, player: Player) -> None:
        delta = self.pos - player.pos
        dist = delta.length()
        min_dist = self.radius + player.radius
        if dist == 0:
            delta = Vector2(1, 0)
            dist = 1

        if dist < min_dist:
            overlap = min_dist - dist
            n = delta / dist
            self.pos += n * overlap

            relative = self.vel - player.vel
            speed = relative.dot(n)
            if speed < 0:
                self.vel -= (1.65 * speed) * n

            self.vel += player.vel * 0.15

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.circle(screen, BLACK, self.pos, self.radius + 1)
        pygame.draw.circle(screen, WHITE, self.pos, self.radius)


class SoccerGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Python Soccer Showdown")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 34, bold=True)
        self.small_font = pygame.font.SysFont("arial", 24)

        self.left_goal = Goal(0, HEIGHT // 2 - 85, 36, 170)
        self.right_goal = Goal(WIDTH - 36, HEIGHT // 2 - 85, 36, 170)

        self.player1 = Player(
            (WIDTH * 0.25, HEIGHT / 2),
            BLUE,
            {
                pygame.K_w: Vector2(0, -1),
                pygame.K_s: Vector2(0, 1),
                pygame.K_a: Vector2(-1, 0),
                pygame.K_d: Vector2(1, 0),
            },
        )

        self.player2 = Player(
            (WIDTH * 0.75, HEIGHT / 2),
            RED,
            {
                pygame.K_UP: Vector2(0, -1),
                pygame.K_DOWN: Vector2(0, 1),
                pygame.K_LEFT: Vector2(-1, 0),
                pygame.K_RIGHT: Vector2(1, 0),
            },
        )

        self.ball = Ball((WIDTH / 2, HEIGHT / 2))
        self.score = [0, 0]
        self.match_seconds = 180
        self.remaining_frames = self.match_seconds * FPS
        self.running = True
        self.game_over = False

    def reset_positions(self) -> None:
        self.player1.pos = Vector2(WIDTH * 0.25, HEIGHT / 2)
        self.player2.pos = Vector2(WIDTH * 0.75, HEIGHT / 2)
        self.player1.vel = Vector2(0, 0)
        self.player2.vel = Vector2(0, 0)
        self.ball.reset()

    def check_goal(self) -> None:
        if self.ball.pos.x < 0 and self.left_goal.y < self.ball.pos.y < self.left_goal.y + self.left_goal.height:
            self.score[1] += 1
            self.reset_positions()
        elif (
            self.ball.pos.x > WIDTH
            and self.right_goal.y < self.ball.pos.y < self.right_goal.y + self.right_goal.height
        ):
            self.score[0] += 1
            self.reset_positions()

    def draw_pitch(self) -> None:
        self.screen.fill(GRASS)
        pygame.draw.rect(self.screen, WHITE, (40, 40, WIDTH - 80, HEIGHT - 80), 4)
        pygame.draw.line(self.screen, WHITE, (WIDTH // 2, 40), (WIDTH // 2, HEIGHT - 40), 4)
        pygame.draw.circle(self.screen, WHITE, (WIDTH // 2, HEIGHT // 2), 78, 4)

        pygame.draw.rect(self.screen, YELLOW, self.left_goal.rect)
        pygame.draw.rect(self.screen, YELLOW, self.right_goal.rect)

    def draw_ui(self) -> None:
        score_text = self.font.render(f"{self.score[0]}  :  {self.score[1]}", True, WHITE)
        self.screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 8))

        remaining_seconds = max(0, self.remaining_frames // FPS)
        mins = remaining_seconds // 60
        secs = remaining_seconds % 60
        clock_text = self.small_font.render(f"Time {mins:01d}:{secs:02d}", True, WHITE)
        self.screen.blit(clock_text, (WIDTH // 2 - clock_text.get_width() // 2, 52))

        controls = self.small_font.render("P1: WASD + F to kick     P2: Arrows + Right Ctrl to kick", True, WHITE)
        self.screen.blit(controls, (WIDTH // 2 - controls.get_width() // 2, HEIGHT - 34))

        if self.game_over:
            if self.score[0] == self.score[1]:
                msg = "Full time! It's a draw. Press R to restart or ESC to quit."
            elif self.score[0] > self.score[1]:
                msg = "Full time! Blue wins. Press R to restart or ESC to quit."
            else:
                msg = "Full time! Red wins. Press R to restart or ESC to quit."

            banner = self.font.render(msg, True, WHITE)
            self.screen.blit(banner, (WIDTH // 2 - banner.get_width() // 2, HEIGHT // 2 - 24))

    def update(self) -> None:
        keys = pygame.key.get_pressed()

        if not self.game_over:
            self.player1.update(keys)
            self.player2.update(keys)

            if keys[pygame.K_f]:
                self.player1.kick(self.ball)
            if keys[pygame.K_RCTRL] or keys[pygame.K_RSHIFT]:
                self.player2.kick(self.ball)

            self.ball.update(self.left_goal, self.right_goal)
            self.ball.resolve_player_collision(self.player1)
            self.ball.resolve_player_collision(self.player2)

            self.check_goal()
            self.remaining_frames -= 1
            if self.remaining_frames <= 0:
                self.game_over = True

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r and self.game_over:
                    self.score = [0, 0]
                    self.remaining_frames = self.match_seconds * FPS
                    self.game_over = False
                    self.reset_positions()

    def run(self) -> None:
        self.reset_positions()
        while self.running:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw_pitch()
            self.player1.draw(self.screen)
            self.player2.draw(self.screen)
            self.ball.draw(self.screen)
            self.draw_ui()
            pygame.display.flip()

        pygame.quit()


def main() -> None:
    SoccerGame().run()


if __name__ == "__main__":
    main()
