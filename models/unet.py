from matplotlib import scale
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.model_zoo as model_zoo
from torchvision.ops import RoIAlign, roi_align

model_urls = {
    'resnet18': 'https://download.pytorch.org/models/resnet18-5c106cde.pth',
    'resnet34': 'https://download.pytorch.org/models/resnet34-333f7ec4.pth',
    'resnet50': 'https://download.pytorch.org/models/resnet50-19c8e357.pth',
    'resnet101': 'https://download.pytorch.org/models/resnet101-5d3b4d8f.pth',
    'resnet152': 'https://download.pytorch.org/models/resnet152-b121ed2d.pth',
}

class BasicBlock(nn.Module):
    expansion = 1
    def __init__(self, inplanes, planes, stride=1, downsample=None, dilation=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, 3, stride, padding=1)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(planes, planes, 3, padding=dilation, dilation=dilation)
        self.bn2 = nn.BatchNorm2d(planes)
        self.inplanes = inplanes
        self.planes = planes
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)
        
        out += residual
        out = self.relu(out)

        return out

class Bottleneck(nn.Module):
    expansion = 4
    def __init__(self, inplanes, planes, stride=1, downsample=None, dilation=1):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride,
                               padding=dilation, bias=False, dilation=dilation)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, planes * 4, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * 4)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride
        self.dilation = dilation

    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)
        out = self.conv3(out)
        out = self.bn3(out)
        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)
        return out

class ResNet(nn.Module):
    def __init__(self, block, layers, strides=(2, 2, 2, 2), dilations=(1, 1, 1, 1)):
        self.inplanes = 64
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=1, padding=3,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        self.layer1 = self._make_layer(block, 64, layers[0], stride=strides[0], dilation=dilations[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=strides[1], dilation=dilations[1])
        self.layer3 = self._make_layer(block, 256, layers[2], stride=strides[2], dilation=dilations[2])
        self.layer4 = self._make_layer(block, 512, layers[3], stride=strides[3], dilation=dilations[3])

        self.inplanes = 1024

        #self.avgpool = nn.AvgPool2d(7, stride=1)
        #self.fc = nn.Linear(512 * block.expansion, 1000)


    def _make_layer(self, block, planes, blocks, stride=1, dilation=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = [block(self.inplanes, planes, stride, downsample, dilation=1)]
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes, dilation=dilation))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x

def resnet18(pretrained=True, **kwargs):
    model = ResNet(BasicBlock, [2, 2, 2, 2], **kwargs)
    if pretrained:
        pretrained_dict=model_zoo.load_url(model_urls['resnet18'])# Modify 'model_dir' according to your own path
        model.load_state_dict(pretrained_dict, strict=False)
        print('Petrain Model Have been loaded!')
    return model

def resnet34(pretrained=True, **kwargs):
    model = ResNet(BasicBlock, [3, 4, 6, 3], **kwargs)
    if pretrained:
        pretrained_dict=model_zoo.load_url(model_urls['resnet34'])# Modify 'model_dir' according to your own path
        model.load_state_dict(pretrained_dict, strict=False)
        print('Petrain Model Have been loaded!')
    return model

def resnet50(pretrained=True, **kwargs):
    model = ResNet(Bottleneck, [3, 4, 6, 3], **kwargs)
    if pretrained:
        state_dict = model_zoo.load_url(model_urls['resnet50'])
        model.load_state_dict(state_dict, strict=False)
        print("model pretrained initialized")
    return model

class Upconv(nn.Module):
    def __init__(self, in_channels, mid_channels, out_channels, scale_factor=1) -> None:
        super(Upconv, self).__init__()
        self.x1_layer = nn.Sequential(
                            nn.Conv2d(in_channels, out_channels, kernel_size=3 ,padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True),
                            nn.UpsamplingBilinear2d(scale_factor=scale_factor),)
        
        self.x2_layer = nn.Sequential(
                            nn.Conv2d(mid_channels, out_channels, kernel_size=3 ,padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True))
        
        self.fusion_layer = nn.Sequential(
                            nn.Conv2d(out_channels*2, out_channels, kernel_size=3 ,padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True))
        
    def forward(self, x1, x2):
        x1 = self.x1_layer(x1)
        x2 = self.x2_layer(x2)
        y = self.fusion_layer(torch.cat((x1,x2),dim=1))
        return y
    
class Upconv_v2(nn.Module):
    def __init__(self, in_channels, mid_channels, out_channels, scale_factor=1) -> None:
        super(Upconv_v2, self).__init__()
        self.x1_layer = nn.Sequential(
                            nn.Conv2d(in_channels, out_channels, kernel_size=3 ,padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True),
                            nn.UpsamplingBilinear2d(scale_factor=scale_factor),)
        
        self.x2_layer = nn.Sequential(
                            nn.Conv2d(mid_channels, out_channels, kernel_size=3 ,padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True))
        
        self.fusion_layer = nn.Sequential(
                            nn.Conv2d(out_channels*2, out_channels, kernel_size=3 ,padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True),
                            nn.Conv2d(out_channels, out_channels, kernel_size=3 ,padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True),)
        
    def forward(self, x1, x2):
        x1 = self.x1_layer(x1)
        x2 = self.x2_layer(x2)
        y = self.fusion_layer(torch.cat((x1,x2),dim=1))
        return y

class TranUpconv(nn.Module):
    def __init__(self, in_channels, mid_channels, out_channels, scale_factor=1) -> None:
        super(TranUpconv, self).__init__()
        self.x1_layer = nn.Sequential(
                            nn.ConvTranspose2d(in_channels, out_channels, kernel_size=3, stride=2, padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True),
                            nn.Conv2d(out_channels, out_channels, kernel_size=3 ,padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True))
        self.x2_layer = nn.Sequential(
                            nn.Conv2d(mid_channels, out_channels, kernel_size=3 ,padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True))
        self.fusion_layer = nn.Sequential(
                            nn.Conv2d(out_channels*2, out_channels, kernel_size=3 ,padding=1),
                            nn.BatchNorm2d(out_channels),
                            nn.ReLU(inplace=True))
        
    def forward(self, x1, x2):
        x1 = self.x1_layer(x1)
        x2 = self.x2_layer(x2)
        h,w = x2.shape[-2:]
        x1 = F.interpolate(x1,(h,w), mode='bilinear')
        y = self.fusion_layer(torch.cat((x1,x2),dim=1))
        return y

class ConvBNReLU(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, padding=1) -> None:
        super(ConvBNReLU, self).__init__()
        self.conv = nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=kernel_size, padding=padding)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
    def forward(self,x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.relu(x)
        return x

class MHCLS(nn.Module):
    def __init__(self, args) -> None:
        super(MHCLS, self).__init__()
        self.args = args
        self.num_heads = args.net_nheads
        self.num_classes = args.net_num_classes
        self.certainty = args.net_certainty
        self.upsample = nn.UpsamplingBilinear2d(scale_factor=2)
        self.mh_classifiers = nn.ModuleList([nn.Sequential(
                                                nn.Conv2d(in_channels=64, out_channels=16, kernel_size=3, padding=1),
                                                nn.BatchNorm2d(16),
                                                nn.ReLU(inplace=True),
                                                nn.Conv2d(in_channels=16, out_channels= self.num_classes, kernel_size=1)) for i in range(self.num_heads)])
        self.mh_vor_classifiers = nn.ModuleList([nn.Sequential(
                                                nn.Conv2d(in_channels=64, out_channels=16, kernel_size=3, padding=1),
                                                nn.BatchNorm2d(16),
                                                nn.ReLU(inplace=True),
                                                nn.Conv2d(in_channels=16, out_channels= self.num_classes, kernel_size=1)) for i in range(self.num_heads)])
        self.mh_certainty = nn.ModuleList([nn.Sequential(
                                                nn.Conv2d(in_channels=64, out_channels=16, kernel_size=3, padding=1),
                                                nn.BatchNorm2d(16),
                                                nn.ReLU(inplace=True),
                                                nn.Conv2d(in_channels=16, out_channels = 1, kernel_size=1)) for i in range(self.num_heads)])
        self.mh_regresser = nn.ModuleList([nn.Sequential(
                                                nn.Conv2d(in_channels=64, out_channels=16, kernel_size=3, padding=1),
                                                nn.BatchNorm2d(16),
                                                nn.ReLU(inplace=True),
                                                nn.Conv2d(in_channels=16, out_channels = 1, kernel_size=1)) for i in range(self.num_heads)])
        if self.args.degree_version in ['v4']:
            self.mh_degree = nn.ModuleList([nn.Sequential(
                                                    nn.Conv2d(in_channels=64, out_channels=128, kernel_size=3, padding=1),
                                                    nn.BatchNorm2d(128),
                                                    nn.ReLU(inplace=True),
                                                    nn.Conv2d(in_channels=128, out_channels=256, kernel_size=3, padding=1),
                                                    nn.BatchNorm2d(256),
                                                    nn.ReLU(inplace=True),
                                                    nn.Conv2d(in_channels=256, out_channels = (4*self.args.net_N+3), kernel_size=1)) for i in range(self.num_heads)])
        elif self.args.degree_version in ['v9', 'v10']:
            self.mh_degree = nn.ModuleList([nn.Sequential(
                                                    nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, padding=1),
                                                    nn.BatchNorm2d(64),
                                                    nn.ReLU(inplace=True),
                                                    nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, padding=1),
                                                    nn.BatchNorm2d(64),
                                                    nn.ReLU(inplace=True),
                                                    nn.Conv2d(in_channels=64, out_channels = 8, kernel_size=1)) for i in range(self.num_heads)])
        else:
            self.mh_degree = nn.ModuleList([nn.Sequential(
                                                    nn.Conv2d(in_channels=64, out_channels=16, kernel_size=3, padding=1),
                                                    nn.BatchNorm2d(16),
                                                    nn.ReLU(inplace=True),
                                                    nn.Conv2d(in_channels=16, out_channels = 1, kernel_size=1)) for i in range(self.num_heads)])
            
        self.mh_counter = nn.ModuleList([nn.Sequential(
                                            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, padding=1),
                                            nn.BatchNorm2d(64),
                                            nn.ReLU(inplace=True),
                                            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, padding=1),
                                            nn.BatchNorm2d(64),
                                            nn.ReLU(inplace=True),
                                            nn.Conv2d(in_channels=64, out_channels=16, kernel_size=3, padding=1),
                                            nn.BatchNorm2d(16),
                                            nn.ReLU(inplace=True),
                                            nn.Conv2d(in_channels=16, out_channels = 1, kernel_size=1)) for i in range(self.num_heads)])
        
    def forward(self, x, deg_map):
        y = []
        vor = []
        cert = []
        heat = []
        deg = []
        count = []
        x = self.upsample(x)
        h,w = deg_map.shape[-2:]
        x = F.interpolate(x, (h,w), mode='bilinear')
        # x_deg = torch.concat((x, deg_map), dim=1)
            
        for ii in range(self.num_heads):
            y.append(self.mh_classifiers[ii](x))
            vor.append(self.mh_vor_classifiers[ii](x))
            cert.append(self.mh_certainty[ii](x))
            heat.append(self.mh_regresser[ii](x))
            deg.append(self.mh_degree[ii](x))
            count.append(self.mh_counter[ii](x))
        return y, vor, cert, heat, deg, count

class Attention(nn.Module):
    def __init__(self, in_channels, out_channels) -> None:
        super(Attention, self).__init__()
        self.in_channels= in_channels
        self.out_channels = out_channels
        
    def forward(self, feat_list):
        for feat in feat_list:
            pass
        return

class UNet(nn.Module):
    def __init__(self, args) -> None:
        super(UNet,self).__init__()
        self.args = args
        
        if args.net_backbone.lower() in ['resnet18', 'res18']:
            self.resnet = resnet18(pretrained=True, strides=(2,2,2,1), dilations=(1,1,1,2))
            scale_factor = [1,2,2,2]
            up_channels = [512, 256, 128, 64, 64]
        elif args.net_backbone.lower() in ['resnet34', 'res34']:
            self.resnet = resnet34(pretrained=True, strides=(2,2,2,1), dilations=(1,1,1,2))
            scale_factor = [1,2,2,2]
            up_channels = [512, 256, 128, 64, 64]
        elif args.net_backbone.lower() in ['resnet50', 'res50']:
            self.resnet = resnet50(pretrained=True, strides=(2,2,2,1), dilations=(1,1,1,2))
            scale_factor = [1,2,2,2]
            up_channels = [2048, 1024, 512, 256, 64]
            
        # self.stem = nn.Sequential(self.resnet.conv1, self.resnet.bn1,self.resnet.relu)
        self.stem = nn.Sequential(self.resnet.conv1, self.resnet.bn1,self.resnet.relu, self.resnet.maxpool)
        self.stage1 = nn.Sequential(self.resnet.layer1)
        self.stage2 = nn.Sequential(self.resnet.layer2)
        self.stage3 = nn.Sequential(self.resnet.layer3)
        self.stage4 = nn.Sequential(self.resnet.layer4)
        if args.net_convtranspose == False:
            self.upconv1 = Upconv(up_channels[0], up_channels[1], up_channels[1], scale_factor=scale_factor[0])
            self.upconv2 = Upconv(up_channels[1], up_channels[2], up_channels[2], scale_factor=scale_factor[1])
            self.upconv3 = Upconv(up_channels[2], up_channels[3], up_channels[3], scale_factor=scale_factor[2])
            self.upconv4 = Upconv(up_channels[3], up_channels[4], up_channels[4], scale_factor=scale_factor[3])
            # self.upconv1 = Upconv_v2(up_channels[0], up_channels[1], up_channels[1], scale_factor=scale_factor[0])
            # self.upconv2 = Upconv_v2(up_channels[1], up_channels[2], up_channels[2], scale_factor=scale_factor[1])
            # self.upconv3 = Upconv_v2(up_channels[2], up_channels[3], up_channels[3], scale_factor=scale_factor[2])
            # self.upconv4 = Upconv_v2(up_channels[3], up_channels[4], up_channels[4], scale_factor=scale_factor[3])
        else:
            self.upconv1 = TranUpconv(up_channels[0], up_channels[1], up_channels[1], scale_factor=scale_factor[0])
            self.upconv2 = TranUpconv(up_channels[1], up_channels[2], up_channels[2], scale_factor=scale_factor[1])
            self.upconv3 = TranUpconv(up_channels[2], up_channels[3], up_channels[3], scale_factor=scale_factor[2])
            self.upconv4 = TranUpconv(up_channels[3], up_channels[4], up_channels[4], scale_factor=scale_factor[3])
        self.nhead_classifer = MHCLS(args)
        
        self.pretrained = nn.ModuleList([self.stem, self.stage1, self.stage2, self.stage3, self.stage4])
        self.new_added = nn.ModuleList([self.upconv1, self.upconv2, self.upconv3, self.upconv4,
                                        self.nhead_classifer])
        
    def forward(self, x):
        deg_map = x[:,3:,:,:]
        x = x[:,:3,:,:]
        
        x1 = self.stem(x)
        x2 = self.stage1(x1)
        x3 = self.stage2(x2)
        x4 = self.stage3(x3)
        x5 = self.stage4(x4)
        # Upconv
        y4 = self.upconv1(x5,x4)
        y3 = self.upconv2(y4,x3)
        y2 = self.upconv3(y3,x2)
        y1 = self.upconv4(y2,x1)
        
        
        y, vor, cert, heat, deg, count = self.nhead_classifer(y1, deg_map)
        return y, vor, cert, heat, deg, count


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser("CellSeg training argument parser.")
    parser.add_argument('--net_stride', default=16, type=int)
    parser.add_argument('--net_num_classes', default=3, type=int)
    args = parser.parse_args()
    net=UNet(args)
    x = torch.zeros((4,3,512,512))
    y = net(x)
    print(y.shape)
