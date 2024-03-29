import logging
import numpy as np
from graphviz import Digraph
from Node import Node
from typing import Tuple, List, Union


class DecisionTreeClassifier:
    """
    A custom implementation of a decision tree classifier.

    This class represents a decision tree for classification tasks.
    It supports basic functionality such as fitting to a dataset, predicting labels for new data, and visualizing the tree structure.

    Parameters
    ----------
    - max_depth (int, optional): The maximum depth of the tree. If None, the tree will grow until all leaves are pure or until it reaches the minimum samples split.
    - min_samples_split (int): The minimum number of samples required to split an internal node. Default is 2.
    - max_features (int, optional): The number of features to consider when looking for the best split. If None, all features are considered.
    - min_impurity_decrease (float): A node will be split if this split induces a decrease of the impurity greater than or equal to this value. Default is 0.0.
    - random_state (int): Controls the randomness of the bootstrapping of the samples used when building trees. Default is 42.
    - debug (bool): If True, the logging level will be set to DEBUG, providing more detailed logging information. Default is False.

    Attributes
    ----------
    - root (Node): The root node of the decision tree after fitting.

    Methods
    -------
    - fit(X, y): Fits the decision tree model to the given dataset.
    - predict(X): Predicts the class labels for the given dataset.
    - visualize_tree(feature_names=None, class_names=None): Generates a visualization of the decision tree using Graphviz.
    """

    def __init__(
        self,
        max_depth: int = None,
        min_samples_split: int = 2,
        max_features: int = None,
        min_impurity_decrease: float = 0.0,
        random_state: int = 42,
        debug: bool = False,
        is_regression: bool = False,
    ) -> None:
        """
        Initializes the DecisionTreeClassifier with the specified parameters.
        """

        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.min_impurity_decrease = min_impurity_decrease

        self.random_state = random_state
        self.random = np.random.RandomState(self.random_state)
        self.root: Node = None
        self.is_regression = is_regression

        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(logging.DEBUG if debug else logging.INFO)

    def __repr__(self) -> str:
        return (
            "DecisionTreeClassifier("
            f"max_depth={self.max_depth}, "
            f"min_samples_split={self.min_samples_split}, "
            f"max_features={self.max_features}, "
            f"min_impurity_decrease={self.min_impurity_decrease}, "
            f"is_regression={self.is_regression}, "
            f"random_state={self.random_state}"
            ")"
        )

    def _get_leaf_value(self, y: np.ndarray) -> Union[int, float]:
        """
        Returns the value of the leaf node based on the type of problem.

        Parameters:
            y (np.ndarray): The target values array.

        Returns:
            Union[int, float]: The value of the leaf node.
        """
        if self.is_regression:
            return np.mean(y)
        else:
            return self._most_common_label(y)

    def _grow_tree(self, X: np.ndarray, y: np.ndarray, depth: int = 0) -> Node:
        """
        Recursively grows the decision tree from the given dataset.

        Parameters:
            X (np.ndarray): The input features array.
            y (np.ndarray): The target values array.
            depth (int): The current depth of the tree.

        Returns:
            Node: The root node of the grown tree.
        """
        n_samples, n_features = X.shape
        n_labels = len(np.unique(y))

        # Stopping criteria
        if (
            (depth >= self.max_depth)
            or (n_labels == 1)
            or (n_samples < self.min_samples_split)
        ):
            self._logger.debug(
                f"Reached leaf node. Depth: {depth}, Samples: {n_samples}, Labels: {n_labels}"
            )
            leaf_value = self._get_leaf_value(y)
            return Node(value=leaf_value)

        if self.max_features is not None:
            features_idxs = self.random.choice(
                n_features, self.max_features, replace=False
            )
        else:
            features_idxs = np.arange(n_features)

        self._logger.debug(f"Considering features: {features_idxs}")
        best_feat, best_thresh, best_gain = self._best_criteria(X, y, features_idxs)

        # Early stopping if no impurity decrease
        if best_gain < self.min_impurity_decrease:
            self._logger.debug(
                f"Early stopping at depth {depth}: No impurity decrease. Creating leaf node with most common label."
            )
            leaf_value = self._get_leaf_value(y)
            return Node(value=leaf_value)

        left_idxs, right_idxs = self._split(X[:, best_feat], best_thresh)

        if len(left_idxs) == 0 or len(right_idxs) == 0:
            self._logger.debug("No split possible. Creating leaf node.")
            leaf_value = self._get_leaf_value(y)
            return Node(value=leaf_value)

        self._logger.debug(
            f"Splitting at depth {depth}: Feature {best_feat} at threshold {best_thresh}, Left samples: {len(left_idxs)}, Right samples: {len(right_idxs)}"
        )

        left = self._grow_tree(X[left_idxs, :], y[left_idxs], depth + 1)
        right = self._grow_tree(X[right_idxs, :], y[right_idxs], depth + 1)
        return Node(best_feat, best_thresh, left, right)

    def _best_criteria(
        self, X: np.ndarray, y: np.ndarray, features_idxs: np.ndarray
    ) -> Tuple[int, float]:
        """
        Finds the best criteria for splitting the dataset.

        Parameters:
            X (np.ndarray): The input features array.
            y (np.ndarray): The target values array.
            features_idxs (np.ndarray): The indices of the features to consider.

        Returns:
            Tuple[int, float]: The index of the best feature and the best threshold for splitting.
        """
        best_gain = -np.inf
        split_idx, split_thresh = None, None

        for idx in features_idxs:
            self._logger.debug(f"Finding best split for feature {idx}")
            feature = X[:, idx]
            thresholds = np.unique(feature)
            for threshold in thresholds:
                gain = self._information_gain(y, feature, threshold)

                if gain > best_gain:
                    best_gain = gain
                    split_idx = idx
                    split_thresh = threshold

        self._logger.debug(
            f"Best split found at feature {split_idx} with threshold {split_thresh} and gain {best_gain}"
        )

        return split_idx, split_thresh, best_gain

    def _information_gain(
        self, y: np.ndarray, feature: np.ndarray, threshold: float
    ) -> float:
        """
        Calculates the information gain of a potential split.

        Parameters:
            y (np.ndarray): The target values array.
            feature (np.ndarray): The feature values array.
            threshold (float): The threshold for splitting.

        Returns:
            float: The information gain of the split.
        """
        if self.is_regression:
            parent_loss = self._mse(y, np.full(y.shape, np.mean(y)))
        else:
            parent_loss = self._entropy(y)

        left_idxs, right_idxs = self._split(feature, threshold)
        if len(left_idxs) == 0 or len(right_idxs) == 0:
            return 0

        n = len(y)
        n_l, n_r = len(left_idxs), len(right_idxs)
        y_l, y_r = y[left_idxs], y[right_idxs]

        if self.is_regression:
            e_l, e_r = (
                self._mse(y_l, np.full(y_l.shape, np.mean(y_l))),
                self._mse(y_r, np.full(y_r.shape, np.mean(y_r))),
            )
        else:
            e_l, e_r = self._entropy(y_l), self._entropy(y_r)

        child_loss = (n_l / n) * e_l + (n_r / n) * e_r

        ig = parent_loss - child_loss

        return ig

    def _mse(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        Calculates the mean squared error between the true and predicted values.

        Parameters:
            y_true (np.ndarray): The true target values.
            y_pred (np.ndarray): The predicted target values.

        Returns:
            float: The mean squared error.
        """
        return np.mean((y_true - y_pred) ** 2)

    def _entropy(self, y: np.ndarray) -> float:
        """
        Calculates the entropy of a dataset.

        Parameters:
            y (np.ndarray): The target values array.

        Returns:
            float: The entropy of the dataset.
        """

        _, counts = np.unique(y, return_counts=True)
        p = counts / len(y)
        entropy = -np.sum(p * np.log2(p))
        return entropy

    def _split(
        self, feature: np.ndarray, threshold: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Splits the dataset based on the given feature and threshold.

        Parameters:
            feature (np.ndarray): The feature values array.
            threshold (float): The threshold for splitting.

        Returns:
            Tuple[np.ndarray, np.ndarray]: The indices of the samples in the left and right splits.
        """
        left_idxs = np.argwhere(feature <= threshold).flatten()
        right_idxs = np.argwhere(feature > threshold).flatten()
        return left_idxs, right_idxs

    def _most_common_label(self, y: np.ndarray) -> int:
        """
        Finds the most common label in the dataset.

        Parameters:
            y (np.ndarray): The target values array.

        Returns:
            int: The most common label.
        """
        if len(y) == 0:
            self._logger.warning("No samples to classify. Returning 0.")
            return None

        common_label = np.bincount(y).argmax()
        self._logger.debug(f"Most common label: {common_label}")
        return common_label

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Fits the decision tree model to the given dataset.

        Parameters:
            X (np.ndarray): The input features array.
            y (np.ndarray): The target values array.
        """
        self._logger.debug("Starting to fit the model.")
        self.root = self._grow_tree(X, y)
        self._logger.debug("Model fitting completed.")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predicts the class labels for the given dataset.

        Parameters:
            X (np.ndarray): The input features array.

        Returns:
            np.ndarray: The predicted class labels.
        """
        self._logger.debug("Starting prediction.")
        predictions = np.array([self._traverse_tree(x, self.root) for x in X])
        self._logger.debug("Prediction completed.")
        return predictions

    def _traverse_tree(self, x: np.ndarray, node: Node) -> Union[int, None]:
        """
        Traverses the decision tree to predict the class label for a single sample.

        Parameters:
            x (np.ndarray): The input features for a single sample.
            node (Node): The current node in the decision tree.

        Returns:
            Union[int, None]: The predicted class label, or None if no prediction could be made.
        """
        if node.is_leaf_node():
            self._logger.debug(f"Reached leaf node. Value: {node.value}")
            return node.value

        if x[node.feature] <= node.threshold:
            self._logger.debug(
                f"Traversing left node. Feature: {node.feature}, Threshold: {node.threshold}"
            )
            return self._traverse_tree(x, node.left)

        else:
            self._logger.debug(
                f"Traversing right node. Feature: {node.feature}, Threshold: {node.threshold}"
            )
            return self._traverse_tree(x, node.right)

    def visualize_tree(
        self, feature_names: List[str] = None, class_names: List[str] = None
    ) -> Digraph:
        """
        Visualizes the decision tree.

        Parameters:
            feature_names (List[str]): The names of the features.
            class_names (List[str]): The names of the classes.

        Returns:
            Digraph: A Graphviz Digraph object representing the decision tree.
        """
        dot = Digraph()

        def add_nodes_edges(node: Node, dot: Digraph) -> None:
            """
            Recursively adds nodes and edges to the Graphviz Digraph.

            Parameters:
                node (Node): The current node in the decision tree.
                dot (Digraph): The Graphviz Digraph object.
            """
            if node.is_leaf_node():
                class_name = class_names[node.value] if class_names else str(node.value)
                # Color leaf nodes green
                dot.node(
                    str(id(node)),
                    label=f"Leaf: {class_name}",
                    shape="ellipse",
                    color="lightgreen",
                    style="filled",
                )
            else:
                feature_name = (
                    feature_names[node.feature]
                    if feature_names
                    else f"Feature {node.feature}"
                )
                # Color decision nodes blue
                dot.node(
                    str(id(node)),
                    label=f"{feature_name}\ <= {node.threshold:.2f}",
                    shape="box",
                    color="lightblue",
                    style="filled",
                )
                if node.left:
                    add_nodes_edges(node.left, dot)
                    dot.edge(
                        str(id(node)), str(id(node.left)), label="True", color="black"
                    )
                if node.right:
                    add_nodes_edges(node.right, dot)
                    dot.edge(
                        str(id(node)), str(id(node.right)), label="False", color="red"
                    )

        add_nodes_edges(self.root, dot)
        return dot
