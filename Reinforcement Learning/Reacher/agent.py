import torch.optim as optim

from config import *
from model import *
from utils.MemoryBuffer import *
from utils.OUNoise import *

BUFFER_SIZE = int(1e5)
BATCH_SIZE = 128
GAMMA = 0.99
TAU = 1e-3
ACTOR_LR = 1e-4
CRITIC_LR = 1e-3
WEIGHT_DECAY = 0        # L2 weight decay

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

class Agent():
    """Interacts with ans learns from the environment"""

    def __init__(self, state_dim, action_dim, max_action_value,seed):

        self.state_dim = state_dim
        self.action_dim = action_dim
        self.seed = seed

        self.actor = ActorNet(state_dim, action_dim, max_action_value, seed).to(device)
        self.actor_target = ActorNet(state_dim, action_dim, max_action_value, seed).to(device)
        self.actor_target.load_state_dict(self.actor.state_dict())
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=ACTOR_LR)

        self.critic = CriticNet(state_dim, action_dim, seed).to(device)
        self.critic_target = CriticNet(state_dim, action_dim, seed).to(device)
        self.critic_target.load_state_dict(self.critic.state_dict())
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=CRITIC_LR, weight_decay=WEIGHT_DECAY)

        if args.prioritized:
            self.memory = PrioritizedReplayBuffer(BUFFER_SIZE, BATCH_SIZE, seed)
        else:
            self.memory = ReplayBuffer(BUFFER_SIZE, BATCH_SIZE, seed)

        # Noise process
        self.noise = OUNoise(action_dim, self.seed)

        self.t_step = 0

    def reset(self):
        self.noise.reset()

    def step(self, state, action, reward, next_state, done):
        # Save experience in replay memory
        self.memory.add(state, action, reward, next_state, done)
        #
        # # # Learn every UPDATE_EXERY time steps
        # if (len(self.memory) > BATCH_SIZE):
        #     experiences = self.memory.sample()
        #     self.learn(experiences, GAMMA)

    def act(self, state, add_noise=True):
        state = torch.from_numpy(state).float().to(device)
        self.actor.eval()
        with torch.no_grad():
            action = self.actor(state).cpu().data.numpy()
        self.actor.train()
        if add_noise:
            action += self.noise.sample()
        return np.clip(action, -1, 1)

    def sample_and_learn(self):
        # Learn, if enough samples are available in memory
        if len(self.memory) > BATCH_SIZE:
            for _ in range(10):
                self.learn()

    def learn(self):

        gamma = GAMMA

        if args.prioritized:
            states, actions, rewards, next_states, dones, indexs, weights = self.memory.sample()
        else:
            states, actions, rewards, next_states, dones = self.memory.sample()


        target_Q = self.critic_target(next_states, self.actor_target(next_states))


        target_Q = rewards + (gamma * target_Q * (1 - dones)).detach()

        current_Q = self.critic(states, actions)


        if args.prioritized:
            errors = torch.abs(current_Q.cpu() - target_Q.cpu()).data.numpy()
            size = errors.shape[0]
            for i in range(size):
                idx = indexs[i]
                self.memory.update(idx, errors[i][0])

            current_Q = current_Q * torch.FloatTensor(weights).to(device)
            target_Q = target_Q * torch.FloatTensor(weights).to(device)
            critic_loss = F.mse_loss(current_Q, target_Q)
        else:
            critic_loss = F.mse_loss(current_Q, target_Q)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), 1)
        self.critic_optimizer.step()

        actor_loss = -self.critic(states, self.actor(states)).mean()
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()

        self.soft_update(self.actor, self.actor_target, TAU)
        self.soft_update(self.critic, self.critic_target, TAU)

    def load(self, actor_path, critic_path):
        self.actor.load_state_dict(torch.load(actor_path), map_location=torch.device('cpu'))
        self.critic.load_state_dict(torch.load(critic_path), map_location=torch.device('cpu'))

    def save(self,actor_path, critic_path):
        torch.save(self.actor.state_dict(), actor_path)
        torch.save(self.critic.state_dict(), critic_path)

    def soft_update(self, local_model, target_model, tau):
        """ Soft update model parameters
        Q_target = tau * Q_local + (1 - tau) * Q_target
        :param local_model (Pytorch model): weights will be copied from
        :param target_model (Pytorch model): weights will be copied to
        :param tau (float): interpolation parameter
        """

        for target_param, local_param in zip(target_model.parameters(), local_model.parameters()):
            target_param.data.copy_(tau * local_param.data + (1 - tau) * target_param.data)