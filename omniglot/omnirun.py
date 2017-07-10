import torch

from omnidata import OmniglotSetsDataset
from omnimodel import Statistician
from omniplot import save_test_grid
from torch import optim
from torch.nn import functional as F
from torch.utils import data
from tqdm import tqdm


def run(model, optimizer, loaders, datasets, epochs, viz_interval=-1, save_interval=-1):
    train_loader, test_loader = loaders
    train_dataset, test_dataset = datasets

    viz_interval = epochs if viz_interval == -1 else viz_interval
    save_interval = epochs if save_interval == -1 else save_interval

    # initial weighting for two term loss
    alpha = 1
    # main training loop
    tbar = tqdm(range(epochs))
    for epoch in tbar:

        # train step (iterate once over training data)
        model.train()
        running_vlb = 0
        for batch in train_loader:
            vlb = model.step(batch, alpha, optimizer, clip_gradients=True)
            running_vlb += vlb

        # update running lower bound
        running_vlb /= (len(train_dataset) // model.batch_size)
        s = "VLB: {:.3f}".format(running_vlb)
        tbar.set_description(s)

        # reduce weight
        alpha *= 0.5

        # evaluate on test set by sampling conditioned on contexts
        model.eval()
        if (epoch + 1) % viz_interval == 0:
            save_path = './output/figures/grid-{}.png'.format(epoch + 1)
            for batch in test_loader:
                inputs, samples = model.sample_conditioned(batch)
                save_test_grid(inputs, samples, save_path)
                break

        # checkpoint model at intervals
        if (epoch + 1) % save_interval == 0:
            save_path ='./output/checkpoints/{}.m'.format(epoch + 1)
            model.save(optimizer, save_path)


def main():
    batch_size = 32
    sample_size = 5
    n_features = 256 * 4 * 4  # output shape of convolutional encoder

    # create datasets
    train_dataset = OmniglotSetsDataset(split='train', augment=True)
    test_dataset = OmniglotSetsDataset(split='test')
    datasets = (train_dataset, test_dataset)

    # create loaders
    train_loader = data.DataLoader(dataset=train_dataset, batch_size=batch_size,
                                   shuffle=True, num_workers=0, drop_last=True)
    test_loader = data.DataLoader(dataset=test_dataset, batch_size=batch_size,
                                  shuffle=False, num_workers=0, drop_last=True)
    loaders = (train_loader, test_loader)

    # create model
    model_kwargs = {
        'batch_size': batch_size,
        'sample_size': sample_size,
        'n_features': n_features,
        'c_dim': 512,
        'n_hidden_statistic': 3,
        'hidden_dim_statistic': 256,
        'n_stochastic': 1,
        'z_dim': 16,
        'n_hidden': 3,
        'hidden_dim': 256,
        'nonlinearity': F.elu,
        'print_vars': False
    }
    model = Statistician(**model_kwargs)
    model.cuda()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)

    restore = False
    if restore:
        # assume we're restoring just for visualization purposes
        path = 'home/conor/Dropbox/msc/thesis/ns/ns/spatial/' \
               'output/checkpoints/300.m'
        state = torch.load(path)
        model.load_state_dict(state['model_state'])
    else:
        epochs = 300
        run(model, optimizer, loaders, datasets, epochs,
            viz_interval=1, save_interval=5)


if __name__ == '__main__':
    main()
