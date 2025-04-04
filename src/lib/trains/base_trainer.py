from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
import torch
from progress.bar import Bar
from models.data_parallel import DataParallel
from utils.utils import AverageMeter
from models.utils import _transpose_and_gather_feat
import numpy as np
def exp_rampup(rampup_length):
    """Exponential rampup from https://arxiv.org/abs/1610.02242"""
    def warpper(epoch):
        if epoch < rampup_length:
            epoch = np.clip(epoch, 0.0, rampup_length)
            phase = 1.0 - epoch / rampup_length
            return float(np.exp(-5.0 * phase * phase))
        else:
            return 1.0
    return warpper
class ModelWithLoss(torch.nn.Module):
  def __init__(self, model, loss):
    super(ModelWithLoss, self).__init__()
    self.model = model
    self.loss = loss
  
  def forward(self, batch,unlabel=False,phase=None):
    outputs = self.model(batch['input'])
    if unlabel:
      loss, loss_stats=outputs[-1]['dim'].mean(),{}
    else:
      loss, loss_stats = self.loss(outputs, batch,phase)
    return outputs[-1], loss, loss_stats
class BaseTrainer(object):
  def __init__(
    self, opt, model, optimizer=None):
    self.opt = opt
    self.optimizer = optimizer
    self.loss_stats, self.loss = self._get_losses(opt)
    self.model_with_loss = ModelWithLoss(model, self.loss)
    self.rampup = exp_rampup(100)
    self.rampup_prob = exp_rampup(100)
    self.rampup_coor = exp_rampup(100)
  def set_device(self, gpus, chunk_sizes, device, distribute = False):
    # if len(gpus) > 1:
    #   self.model_with_loss = DataParallel(
    #     self.model_with_loss, device_ids=gpus,
    #     chunk_sizes=chunk_sizes).to(device)
    # else:
    #   self.model_with_loss = self.model_with_loss.to(device)
    #
    # for state in self.optimizer.state.values():
    #   for k, v in state.items():
    #     if isinstance(v, torch.Tensor):
    #       state[k] = v.to(device=device, non_blocking=True)
    if len(gpus) > 1 and not distribute:
      self.model_with_loss = DataParallel(
          self.model_with_loss, device_ids=gpus,
          chunk_sizes=chunk_sizes).to(device)
    else:
      self.model_with_loss = self.model_with_loss.to(device)
    for state in self.optimizer.state.values():
      for k, v in state.items():
        if isinstance(v, torch.Tensor):
          state[k] = v.to(device=device, non_blocking=True)

  def run_epoch(self, phase, epoch, data_loader,unlabel_loader1=None,unlabel_loader2=None,unlabel_set=None,iter_num=None,data_loder2=None):
    model_with_loss = self.model_with_loss
    if phase == 'train':
      model_with_loss.train()
    else:
      # if len(self.opt.gpus) > 1:
      #   model_with_loss = self.model_with_loss.module
      model_with_loss.eval()
      torch.cuda.empty_cache()

    opt = self.opt
    results = {}
    data_time, batch_time = AverageMeter(), AverageMeter()
    avg_loss_stats = {l: AverageMeter() for l in self.loss_stats}
    num_iters = len(data_loader) if opt.num_iters < 0 else opt.num_iters
    bar = Bar('{}/{}'.format("3D detection", opt.exp_id), max=num_iters)
    end = time.time()

    for iter_id, batch in enumerate(data_loader):
      if iter_id >= num_iters:
        break
      data_time.update(time.time() - end)

      for k in batch:
        if k != 'meta':
          batch[k] = batch[k].to(device=opt.device, non_blocking=True)
      coor_weight=self.rampup_coor(epoch)
      if coor_weight< self.opt.coor_thresh:
          coor_weight=0
      output, loss, loss_stats = model_with_loss(batch,phase=phase)
      loss = loss['hm_loss'].mean() * opt.hm_weight + \
             loss['wh_loss'].mean() * opt.wh_weight + \
             loss['off_loss'].mean() * opt.off_weight + \
             loss['hp_loss'].mean() * opt.hp_weight + \
             loss['hp_offset_loss'].mean() * opt.off_weight + \
             loss['hm_hp_loss'].mean() * opt.hm_hp_weight + \
             loss['dim_loss'].mean() *opt.dim_weight + \
             loss['pix_dist_loss'].mean() *opt.pix_dist_weight + \
             loss['rot_loss'].mean() * opt.rot_weight + \
             loss['prob_loss'].mean()*self.rampup_prob(epoch)+\
             loss['coor_loss'].mean()*coor_weight
      # loss = loss['hm_loss'].mean() * opt.hm_weight + \
      #        loss['hp_loss'].mean() * opt.hp_weight + \
      #        loss['dim_loss'].mean() * opt.dim_weight + \
      #        loss['rot_loss'].mean() * opt.rot_weight + \
      #        loss['prob_loss'].mean() * self.rampup_prob(epoch) + \
      #        loss['coor_loss'].mean() * coor_weight
      if phase == 'train':
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
      batch_time.update(time.time() - end)
      end = time.time()

      Bar.suffix = '{phase}: [{0}][{1}/{2}]|Tot: {total:} |ETA: {eta:} '.format(
        epoch, iter_id, num_iters, phase=phase,
        total=bar.elapsed_td, eta=bar.eta_td)
      for l in avg_loss_stats:
        avg_loss_stats[l].update(
          loss_stats[l].mean().item(), batch['input'].size(0))
        Bar.suffix = Bar.suffix + '|{} {:.4f} '.format(l, avg_loss_stats[l].avg)
      if not opt.hide_data_time:
        Bar.suffix = Bar.suffix + '|Data {dt.val:.3f}s({dt.avg:.3f}s) ' \
          '|Net {bt.avg:.3f}s'.format(dt=data_time, bt=batch_time)
      if opt.print_iter > 0:
        if iter_id % opt.print_iter == 0:
          print('{}/{}| {}'.format(opt.task, opt.exp_id, Bar.suffix)) 
      else:
        bar.next()
      
      if opt.debug > 0:
        self.debug(batch, output, iter_id)
      
      if opt.test:
        self.save_result(output, batch, results)
      del output, loss, loss_stats
    
    bar.finish()
    ret = {k: v.avg for k, v in avg_loss_stats.items()}
    ret['time'] = bar.elapsed_td.total_seconds() / 60.
    return ret, results
  
  def debug(self, batch, output, iter_id):
    raise NotImplementedError

  def save_result(self, output, batch, results):
    raise NotImplementedError

  def _get_losses(self, opt):
    raise NotImplementedError
  
  def val(self, epoch, data_loader):
    return self.run_epoch('val', epoch, data_loader)

  def train(self, epoch, data_loader,unlabel_loader1=None,unlabel_loader2=None,unlabel_set=None,iter_num=None,uncert=None):
    return self.run_epoch('train', epoch, data_loader,unlabel_loader1,unlabel_loader2,unlabel_set,iter_num,uncert)
