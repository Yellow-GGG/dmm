import torch
import os
from torch import nn
from torch import optim
from torch.utils.data import DataLoader
from torchvision import datasets
from torchvision import transforms
from accelerate import Accelerator
from tqdm import tqdm

class MNIST_linear(nn.Module):
    def __init__(self):
        super().__init__()
        self.flat = nn.Flatten()
        self.net = nn.Linear(784, 10, bias=False)
    def forward(self, x):
        return self.net(self.flat(x))
    def re_init(self):
        nn.init.normal_(self.net.weight)

class trainer():
    def __init__(self):
        if not os.path.exists("../datasets/"):
            os.makedirs("../datasets/")
        if not os.path.exists("../datasets/MNIST_models/"):
            os.makedirs("../datasets/MNIST_models/")
        self.MNIST_train = datasets.MNIST(
            root="../datasets/",
            train=True,
            download=True,
            transform=transforms.ToTensor()
        )
        self.MNIST_test = datasets.MNIST(
            root="../datasets/",
            train=False,
            download=True,
            transform=transforms.ToTensor()
        )
        self.accelerator = Accelerator()
        self.device = self.accelerator.device
        self.loss_fn = nn.CrossEntropyLoss()
        self.model = MNIST_linear().to(self.device)
        self.optimizer = optim.SGD(self.model.parameters(), lr=0.01)
        self.train_loader = DataLoader(self.MNIST_train, 128)
        self.test_loader = DataLoader(self.MNIST_test, 128)
        self.model, self.optimizer = self.accelerator.prepare(
                self.model, self.optimizer)
        self.train_loader, self.test_loader = self.accelerator.prepare(
                self.train_loader, self.test_loader)
        self.model_count = 0

    def train(self):
        self.model.train()
        for _ in tqdm(range(10)):
            for (X, y) in self.train_loader:
                pred = self.model(X)
                loss = self.loss_fn(pred, y)
                self.accelerator.backward(loss)
                self.optimizer.step()
                self.optimizer.zero_grad()
        torch.save(self.model.state_dict(), f"../datasets/MNIST_models/{self.model_count}.pt")
        print(f"Finished training model [{self.model_count}/1024]")
        self.model_count += 1

    def test(self):
        size = len(self.MNIST_test)
        num_batches = len(self.test_loader)
        self.model.eval()
        tloss, tcorrect = 0.0, 0.0
        with torch.no_grad():
            for X, y in self.test_loader:
                X = X.to(self.device)
                y = y.to(self.device)
                pred = self.model(X)
                tloss += self.loss_fn(pred, y)
                tcorrect += (pred.argmax(1) == y).type(torch.float).sum().item()
        tloss /= num_batches
        #tloss = tloss.item()
        tcorrect /= size
        tcorrect *= 100
        print(f"Current Test Error: {tloss:>8f}")
        print(f"Current Test Accuracy: {tcorrect:>0.01f}%")
        #return (tloss, tcorrect)

    def generate_model_data(self):
        while self.model_count < 2048:
            self.train()

if __name__ == "__main__":
    t = trainer()
    t.generate_model_data()
