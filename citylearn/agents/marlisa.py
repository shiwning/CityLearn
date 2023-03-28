from copy import deepcopy
from typing import List, Tuple
import numpy as np

try:
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LinearRegression
except (ModuleNotFoundError, ImportError) as e:
    raise Exception("This functionality requires you to install scikit-learn. You can install scikit-learn by : pip scikit-learn, or for more detailed instructions please visit https://scikit-learn.org/stable/install.html.")

try:
    import torch
except (ModuleNotFoundError, ImportError) as e:
    raise Exception("This functionality requires you to install torch. You can install torch by : pip install torch torchvision, or for more detailed instructions please visit https://pytorch.org.")

from citylearn.agents.sac import SAC
from citylearn.preprocessing import Encoder, NoNormalization, PeriodicNormalization, RemoveFeature
from citylearn.rl import RegressionBuffer

class MARLISA(SAC):
    __COORDINATION_VARIABLE_COUNT = 2

    def __init__(
        self, *args, regression_buffer_capacity: int = None, start_regression_time_step: int = None, 
        regression_frequency: int = None, information_sharing: bool = None, pca_compression: float = None, iterations: int = None, **kwargs
    ):
        self.__coordination_variables_history = None
        self.information_sharing = information_sharing

        super().__init__(*args, **kwargs)

        self.regression_buffer_capacity = regression_buffer_capacity
        self.start_regression_time_step = start_regression_time_step
        self.pca_compression = pca_compression
        self.iterations = iterations
        self.regression_frequency = regression_frequency

        # internally defined
        self.regression_buffer = [RegressionBuffer(int(self.regression_buffer_capacity)) for _ in self.action_space]
        self.state_estimator = [LinearRegression() for _ in self.action_space]
        self.pca = [None for _ in self.action_space]
        self.pca_flag = [False for _ in self.action_dimension]
        self.regression_flag = [0 for _ in self.action_dimension]
        self.energy_size_coefficient = None
        self.total_coefficient = None
        self.regression_encoders = self.set_regression_encoders()
        self.set_energy_coefficients()
        self.set_pca()

    @property
    def regression_buffer_capacity(self) -> int:
        return self.__regression_buffer_capacity

    @property
    def start_regression_time_step(self) -> int:
        return self.__start_regression_time_step

    @property
    def regression_frequency(self) -> int:
        return self.__regression_frequency

    @property
    def information_sharing(self) -> bool:
        return self.__information_sharing

    @property
    def pca_compression(self) -> float:
        return self.__pca_compression

    @property
    def iterations(self) -> int:
        return self.__iterations

    @property
    def coordination_variables_history(self) -> List[float]:
        return self.__coordination_variables_history

    @SAC.hidden_dimension.setter
    def hidden_dimension(self, hidden_dimension: List[float]):
        hidden_dimension = [400, 300] if hidden_dimension is None else hidden_dimension
        SAC.hidden_dimension.fset(self, hidden_dimension)

    @SAC.batch_size.setter
    def batch_size(self, batch_size: int):
        batch_size = 100 if batch_size is None else batch_size
        SAC.batch_size.fset(self, batch_size)

    @regression_buffer_capacity.setter
    def regression_buffer_capacity(self, regression_buffer_capacity: int):
        self.__regression_buffer_capacity = 3e4 if regression_buffer_capacity is None else regression_buffer_capacity

    @regression_frequency.setter
    def regression_frequency(self, regression_frequency: int):
        self.__regression_frequency = 2500 if regression_frequency is None else regression_frequency

    @start_regression_time_step.setter
    def start_regression_time_step(self, start_regression_time_step: int):
        start_regression_time_step = self.start_training_time_step - 1 if start_regression_time_step is None else start_regression_time_step
        assert start_regression_time_step < self.start_training_time_step, 'start_regression_time_step must be < start_training_time_step'
        self.__start_regression_time_step = start_regression_time_step

    @information_sharing.setter
    def information_sharing(self, information_sharing: bool):
        self.__information_sharing = False if information_sharing is None else information_sharing

    @pca_compression.setter
    def pca_compression(self, pca_compression: float):
        self.__pca_compression = 1.0 if pca_compression is None else pca_compression

    @iterations.setter
    def iterations(self, iterations: int):
        self.__iterations = 2 if iterations is None else iterations

    def add_to_buffer(self, observations: List[List[float]], actions: List[List[float]], reward: List[float], next_observations: List[List[float]], done: bool):
        r"""Update replay buffer.

        Parameters
        ----------
        observations : List[List[float]]
            Previous time step observations.
        actions : List[List[float]]
            Previous time step actions.
        reward : List[float]
            Current time step reward.
        next_observations : List[List[float]]
            Current time step observations.
        done : bool
            Indication that episode has ended.
        """

        # Run once the regression model has been fitted
        # Normalize all the observations using periodical normalization, one-hot encoding, or -1, 1 scaling. It also removes observations that are not necessary (solar irradiance if there are no solar PV panels).

        for i, (o, a, r, n, c0, c1) in enumerate(zip(observations, actions, reward, next_observations, self.coordination_variables_history[0], self.coordination_variables_history[1])):
            if self.information_sharing:
                # update regression buffer
                variables = np.hstack(np.concatenate((self.get_encoded_regression_variables(i, o), a)))
                # The targets are the net electricity consumption.
                target = self.get_encoded_regression_targets(i, n)
                self.regression_buffer[i].push(variables, target)
            
            else:
                pass

            if self.regression_flag[i] > 1:
                o = self.get_encoded_observations(i, o)
                n = self.get_encoded_observations(i, n)

                # Only executed during the random exploration phase. Pushes unnormalized tuples into the replay buffer.
                if self.information_sharing:
                    o = np.hstack(np.concatenate((o, c0), dtype=float))
                    n = np.hstack(np.concatenate((n, c1), dtype=float))
                
                else:
                    pass

                # Executed during the training phase. States and rewards pushed into the replay buffer are normalized and processed using PCA.
                if self.pca_flag[i]:
                    o = self.get_normalized_observations(i, o)
                    o = self.pca[i].transform(o.reshape(1, -1))[0]
                    n = self.get_normalized_observations(i, n)
                    n = self.pca[i].transform(n.reshape(1, -1))[0]
                    r = self.get_normalized_reward(i, r)
                else:
                    pass

                self.replay_buffer[i].push(o, a, r, n, done)

            else:
                pass

            if self.time_step >= self.start_regression_time_step\
                and (self.regression_flag[i] < 2 or self.time_step%self.regression_frequency == 0):
                if self.information_sharing:
                    self.state_estimator[i].fit(self.regression_buffer[i].x, self.regression_buffer[i].y)
                
                else:
                    pass

                if self.regression_flag[i] < 2:
                    self.regression_flag[i] += 1
                
                else:
                    pass

            else:
                pass

            if self.time_step >= self.start_training_time_step and self.batch_size <= len(self.replay_buffer[i]):
                # This code only runs once. Once the random exploration phase is over, we normalize all the states and rewards to make them have mean=0 and std=1, and apply PCA. We push the normalized compressed values back into the buffer, replacing the old buffer.
                if not self.pca_flag[i]:
                    # calculate normalized observations and rewards
                    X = np.array([j[0] for j in self.replay_buffer[i].buffer], dtype=float)
                    self.norm_mean[i] = np.nanmean(X, axis=0)
                    self.norm_std[i] = np.nanstd(X, axis=0) + 1e-5
                    X = self.get_normalized_observations(i, X)
                    self.pca[i].fit(X)

                    R = np.array([j[2] for j in self.replay_buffer[i].buffer], dtype=float)
                    self.r_norm_mean[i] = np.nanmean(R, dtype=float)
                    self.r_norm_std[i] = np.nanstd(R, dtype=float)/self.reward_scaling + 1e-5

                    # update buffer with normalization
                    self.replay_buffer[i].buffer = [(
                        np.hstack(self.pca[i].transform(self.get_normalized_observations(i, o).reshape(1,-1))[0]),
                        a,
                        self.get_normalized_reward(i, r),
                        np.hstack(self.pca[i].transform(self.get_normalized_observations(i, n).reshape(1,-1))[0]),
                        d
                    ) for o, a, r, n, d in self.replay_buffer[i].buffer]
                    self.pca_flag[i] = True
                    self.normalized[i] = True
                
                else:
                    pass

                for _ in range(self.update_per_time_step):
                    o, a, r, n, d = self.replay_buffer[i].sample(self.batch_size)
                    tensor = torch.cuda.FloatTensor if self.device.type == 'cuda' else torch.FloatTensor
                    o = tensor(o).to(self.device)
                    n = tensor(n).to(self.device)
                    a = tensor(a).to(self.device)
                    r = tensor(r).unsqueeze(1).to(self.device)
                    d = tensor(d).unsqueeze(1).to(self.device)

                    with torch.no_grad():
                        # Update Q-values. First, sample an action from the Gaussian policy/distribution for the current (next) observation and its associated log probability of occurrence.
                        new_next_actions, new_log_pi, _ = self.policy_net[i].sample(n)

                        # The updated Q-value is found by subtracting the logprob of the sampled action (proportional to the entropy) to the Q-values estimated by the target networks.
                        target_q_values = torch.min(
                            self.target_soft_q_net1[i](n, new_next_actions),
                            self.target_soft_q_net2[i](n, new_next_actions),
                        ) - self.alpha*new_log_pi
                        q_target = r + (1 - d)*self.discount*target_q_values

                    # Update Soft Q-Networks
                    q1_pred = self.soft_q_net1[i](o, a)
                    q2_pred = self.soft_q_net2[i](o, a)
                    q1_loss = self.soft_q_criterion(q1_pred, q_target)
                    q2_loss = self.soft_q_criterion(q2_pred, q_target)
                    self.soft_q_optimizer1[i].zero_grad()
                    q1_loss.backward()
                    self.soft_q_optimizer1[i].step()
                    self.soft_q_optimizer2[i].zero_grad()
                    q2_loss.backward()
                    self.soft_q_optimizer2[i].step()

                    # Update Policy
                    new_actions, log_pi, _ = self.policy_net[i].sample(o)
                    q_new_actions = torch.min(
                        self.soft_q_net1[i](o, new_actions),
                        self.soft_q_net2[i](o, new_actions)
                    )
                    policy_loss = (self.alpha*log_pi - q_new_actions).mean()
                    self.policy_optimizer[i].zero_grad()
                    policy_loss.backward()
                    self.policy_optimizer[i].step()

                    # Soft Updates
                    for target_param, param in zip(self.target_soft_q_net1[i].parameters(), self.soft_q_net1[i].parameters()):
                        target_param.data.copy_(target_param.data*(1.0 - self.tau) + param.data*self.tau)

                    for target_param, param in zip(self.target_soft_q_net2[i].parameters(), self.soft_q_net2[i].parameters()):
                        target_param.data.copy_(target_param.data*(1.0 - self.tau) + param.data*self.tau)

            else:
                pass

    def get_post_exploration_actions(self, observations: List[List[float]], deterministic: bool) -> List[List[float]]:
        func = {
            True: self.get_post_exploration_actions_with_information_sharing,
            False: self.get_post_exploration_actions_without_information_sharing
        }[self.information_sharing]
        actions, coordination_variables = func(observations, deterministic)
        self.__coordination_variables_history[0] = deepcopy(self.__coordination_variables_history[1])
        self.__coordination_variables_history[1] = coordination_variables[0:]
        
        return actions

    def get_exploration_actions(self, observations: List[List[float]]) -> List[List[float]]:
        func = {
            True: self.get_exploration_actions_with_information_sharing,
            False: self.get_exploration_actions_without_information_sharing
        }[self.information_sharing]
        actions, coordination_variables = func(observations)
        self.__coordination_variables_history[0] = deepcopy(self.__coordination_variables_history[1])
        self.__coordination_variables_history[1] = coordination_variables[0:]
        
        return actions

    def get_post_exploration_actions_with_information_sharing(self, observations: List[List[float]], deterministic: bool) -> Tuple[List[List[float]], List[List[float]]]:
        agent_count = len(self.action_dimension)
        actions = [None for _ in range(agent_count)]
        action_order = list(range(agent_count))
        next_agent_ixs = [sorted(action_order)[action_order[(i + 1)%agent_count]] for i in range(agent_count)]
        coordination_variables = [[0.0, 0.0] for _ in range(agent_count)] 
        expected_demand = [0.0 for _ in range(agent_count)]
        total_demand = 0.0
        
        for i in range(self.iterations):
            capacity_dispatched = 0.0

            for c, n, o, o_ in zip(action_order, next_agent_ixs, observations, observations):
                o = self.get_encoded_observations(c, o)
                o = np.hstack(np.concatenate((o, coordination_variables[c])))
                o = self.get_normalized_observations(c, o)
                o = self.pca[c].transform(o.reshape(1,-1))[0]
                o = torch.FloatTensor(o).unsqueeze(0).to(self.device)
                result = self.policy_net[i].sample(o)
                a = result[2] if self.time_step >= self.deterministic_start_time_step or deterministic else result[0]
                a = list(a.detach().cpu().numpy()[0])
                actions[c] = a
                expected_demand[c] = self.predict_demand(c, o_, a)

                if i == self.iterations - 1 and c == action_order[-1]:
                    pass
                else:
                    total_demand += expected_demand[c] - expected_demand[n]
                    coordination_variables[n][0] = total_demand/self.total_coefficient

                coordination_variables[c][1] = capacity_dispatched
                capacity_dispatched += self.energy_size_coefficient[c]
        
        return actions, coordination_variables

    def get_post_exploration_actions_without_information_sharing(self, observations: List[List[float]], deterministic: bool) -> Tuple[List[List[float]], List[List[float]]]:
        agent_count = len(self.action_dimension)
        actions = [None for _ in range(agent_count)]
        coordination_variables = [[0.0, 0.0] for _ in range(agent_count)]

        for i, o in enumerate(observations):
            o = self.get_encoded_observations(i, o)
            o = self.get_normalized_observations(i, o)
            o = self.pca[i].transform(o.reshape(1,-1))[0]
            o = torch.FloatTensor(o).unsqueeze(0).to(self.device)
            result = self.policy_net[i].sample(o)
            a = result[2] if self.time_step >= self.deterministic_start_time_step or deterministic else result[0]
            a = list(a.detach().cpu().numpy()[0])
            actions[i] = a
        
        return actions, coordination_variables

    def get_exploration_actions_with_information_sharing(self, observations: List[List[float]]) -> Tuple[List[List[float]], List[List[float]]]:
        actions, coordination_variables = self.get_exploration_actions_without_information_sharing(observations)
    
        if self.time_step > self.start_regression_time_step:
            agent_count = len(self.action_dimension)
            action_order = list(range(agent_count))
            np.random.shuffle(action_order)
            expected_demand = [self.predict_demand(i, o, a) for i, (o, a) in enumerate(zip(observations, actions))]
            coordination_variables = [[
                (sum(expected_demand) - expected_demand[i])/self.total_coefficient,
                sum([self.energy_size_coefficient[j] for j in action_order[0:action_order.index(i)]])
            ] for i in range(agent_count)]
        
        else:
            pass
        
        return actions, coordination_variables

    def get_exploration_actions_without_information_sharing(self, observations: List[List[float]]) -> Tuple[List[List[float]], List[List[float]]]:
        actions = super().get_exploration_actions(observations)
        coordination_variables = [[0.0, 0.0] for _ in range(len(self.action_dimension))]

        return actions, coordination_variables

    def predict_demand(self, index: int, observations: List[float], actions: List[float]) -> float:
        return self.state_estimator[index].predict(self.get_regression_variables(index, observations, actions).reshape(1, -1))[0]
    
    def get_regression_variables(self, index: int, observations: List[float], actions: List[float]) -> List[float]:
        return np.hstack(np.concatenate((self.get_encoded_regression_variables(index, observations), actions)))

    def get_encoded_regression_variables(self, index: int, observations: List[float]) -> List[float]:
        net_electricity_consumption_ix = self.observation_names[index].index('net_electricity_consumption')
        o = observations[0:]
        del o[net_electricity_consumption_ix]
        e = self.regression_encoders[index][0:]
        del e[net_electricity_consumption_ix]
        
        return np.array([j for j in np.hstack(e*np.array(o, dtype=float)) if j != None], dtype=float).tolist()

    def get_encoded_regression_targets(self, index: int, observations: List[float]) -> float:
        net_electricity_consumption_ix = self.observation_names[index].index('net_electricity_consumption')
        o = observations[net_electricity_consumption_ix]
        e = self.regression_encoders[index][net_electricity_consumption_ix]
        
        return e*o

    def set_pca(self):
        addition = self.__COORDINATION_VARIABLE_COUNT if self.information_sharing else 0
        
        for i, s in enumerate(self.observation_space):
            n_components = int((self.pca_compression)*(addition + len(self.get_encoded_observations(i, s.low))))
            self.pca[i] = PCA(n_components=n_components)

    def set_energy_coefficients(self):
        self.energy_size_coefficient = []
        self.total_coefficient = 0

        for b in self.building_information:
            coef = b['annual_dhw_demand']/.9 \
                + b['annual_cooling_demand']/3.5 \
                    + b['annual_heating_demand']/3.5 \
                        + b['annual_nonshiftable_electrical_demand'] \
                            - b['solar_power']*8760/6.0
            coef = max(0.3*(coef + b['solar_power']*8760/6.0), coef)/8760
            self.energy_size_coefficient.append(coef)
            self.total_coefficient += coef

        self.energy_size_coefficient = [c/self.total_coefficient for c in self.energy_size_coefficient]

    def set_regression_encoders(self) -> List[List[Encoder]]:
        r"""Get observation value transformers/encoders for use in MARLISA agent internal regression model.

        The encoder classes are defined in the `preprocessing.py` module and include `PeriodicNormalization` for cyclic observations,
        `OnehotEncoding` for categorical obeservations, `RemoveFeature` for non-applicable observations given available storage systems and devices
        and `Normalize` for observations with known minimum and maximum boundaries.
        
        Returns
        -------
        encoders : List[Encoder]
            Encoder classes for observations ordered with respect to `active_observations`.
        """

        encoders = []
        remove_features = [
            'outdoor_dry_bulb_temperature', 'outdoor_dry_bulb_temperature_predicted_6h',
            'outdoor_dry_bulb_temperature_predicted_12h','outdoor_dry_bulb_temperature_predicted_24h',
            'outdoor_relative_humidity', 'outdoor_relative_humidity_predicted_6h',
            'outdoor_relative_humidity_predicted_12h','outdoor_relative_humidity_predicted_24h',
            'diffuse_solar_irradiance', 'diffuse_solar_irradiance_predicted_6h',
            'diffuse_solar_irradiance_predicted_12h', 'diffuse_solar_irradiance_predicted_24h',
            'direct_solar_irradiance', 'direct_solar_irradiance_predicted_6h',
            'direct_solar_irradiance_predicted_12h', 'direct_solar_irradiance_predicted_24h',
        ]

        for o, s in zip(self.observation_names, self.observation_space):
            e = []

            for i, n in enumerate(o):
                if n in ['month', 'hour']:
                    e.append(PeriodicNormalization(s.high[i]))
            
                elif n in remove_features:
                    e.append(RemoveFeature())
            
                else:
                    e.append(NoNormalization())

            encoders.append(e)

        return encoders

    def set_networks(self):
        internal_observation_count = self.__COORDINATION_VARIABLE_COUNT if self.information_sharing else 0
        return super().set_networks(internal_observation_count=internal_observation_count)

    def reset(self):
        super().reset()
        self.__coordination_variables_history = [
            [[0.0]*self.__COORDINATION_VARIABLE_COUNT for _ in self.action_dimension] for _ in range(2)
        ]