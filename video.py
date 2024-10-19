from PyQt5.QtWidgets import QFileDialog, QApplication, QWidget, QDesktopWidget, QTabWidget, QTableWidgetItem
from PyQt5.QtGui import QPainter, QPixmap, QImage, QPen, QPolygon
from PyQt5.QtCore import QUrl, Qt, QPoint
import cv2, pickle, cvzone, numpy as np, json, threading, os
from playsound import playsound
from video_ import Ui_Form

# 鼠标点击时记录位置坐标用
pos1 = (0, 0)
pos2 = (0, 0)


class videoPlayer(QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        '''初始化'''
        self.cap = ''
        # 规则车位记录
        self.last_parkingPath = ''
        self.last_videoPath = ''
        # 非规则车位记录
        self.last_parkingPathAb = ''
        self.last_videoPathAb = ''
        # 配置信息
        self.cfg = ''
        # 摄像头账号密码
        self.cameraUserPwd = ''
        # 停车位长宽
        self.width = 0
        self.height = 0
        # 可以自定义的参数
        self.GaussianBlur_ksize = 0
        self.adaptiveThreshold_blockSize = 0
        self.adaptiveThreshold_c = 0
        self.medianBlur_ksize = 0
        self.dilate_kernel = 0
        # 默认使用默认配置
        self.config(0)
        # 车位记录列表
        self.posList = []
        # 车位索引标识
        self.nextLabel = 1
        # 用于非规则车位选择时暂存车位列表
        self.temPosList = []
        # 先初始化posList 再Default赋值
        self.Default()
        # 车位统计变化监控与车位统计
        self.lastSpaceCarParkCount = 0
        self.spaceCarParkCount = 0
        '''函数 信号槽'''
        # 像素阈值
        self.thresholdSlider.valueChanged.connect(self.thresholdSliderValueChanged)
        # 像素阈值保存
        self.btn_saveThreshold.clicked.connect(self.saveThresholdSliderValue)
        # 默认配置
        self.rbtn_commonCfg.toggled.connect(lambda: self.commonCfg(self.rbtn_commonCfg.isChecked()))
        # 自定义配置
        self.rbtn_customCfg.toggled.connect(lambda: self.customCfg(self.rbtn_customCfg.isChecked()))
        # 自定义配置页面 启动隐藏
        self.widget_custom.setVisible(False)
        # 保存自定义配置
        self.btn_saveCfg.clicked.connect(self.saveConfig)
        # 保存配置按钮禁用
        self.btn_saveCfg.setEnabled(False)
        # 剩余车位预警
        self.cbtn_warning.toggled.connect(lambda: self.parkWarning(self.cbtn_warning.isChecked()))
        # 车位是否为规则车位
        self.cbtn_parkShape.toggled.connect(lambda: self.parkShape(self.cbtn_parkShape.isChecked()))
        # 停车场车位长宽数据选择按钮
        self.btn_wh.clicked.connect(self.selectWidthHeight)
        # 停车场车位长宽数据保存按钮
        self.btn_savewh.clicked.connect(self.saveWidthHeight)
        # 停车场车位选择按钮
        self.btn_parking.clicked.connect(self.selectParking)
        # 停车场车位清空按钮
        self.btn_clearParking.clicked.connect(self.clearParking)
        # 停车场车位保存按钮
        self.btn_saveParking.clicked.connect(self.saveParking)
        # 视频选择按钮
        self.btn_video.clicked.connect(self.selectVideo)
        # 视频关闭按钮
        self.btn_videoClose.clicked.connect(self.closeVideo)
        # 摄像头ip地址变化触发验证规则
        self.path_camera.textChanged.connect(self.ipAddressValidator)
        # 摄像头选择按钮
        self.btn_camera.clicked.connect(self.selectCamera)
        # 摄像头视频关闭按钮
        self.btn_cameraClose.clicked.connect(self.closeCamera)
        # 图片or视频控制
        self.is_process_widthheight = False
        self.is_process_image = False
        self.is_process_video = False
        self.is_process_audio = False

    # 页面居中显示
    def center(self):
        # 获取屏幕坐标系
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口坐标系
        size = self.geometry()
        newLeft = (screen.width() - size.width()) / 2
        # 80为去除底部任务栏的影响
        newTop = (screen.height() - 80 - size.height()) / 2
        self.move(int(newLeft), int(newTop))

    # 按钮能否使用
    def btn_ableOrEnable(self, ableOrEnableFlag):
        if ableOrEnableFlag:
            self.btn_parking.setEnabled(True)
            self.btn_video.setEnabled(True)
            self.rbtn_commonCfg.setEnabled(True)
            self.rbtn_customCfg.setEnabled(True)
            self.cbtn_warning.setEnabled(True)
        else:
            self.btn_parking.setEnabled(False)
            self.btn_video.setEnabled(False)
            self.rbtn_commonCfg.setEnabled(False)
            self.rbtn_customCfg.setEnabled(False)
            self.cbtn_warning.setEnabled(False)
        self.btn_savewh.setEnabled(False)
        self.btn_clearParking.setEnabled(False)
        self.btn_saveParking.setEnabled(False)
        self.thresholdSlider.setEnabled(False)
        self.btn_saveThreshold.setEnabled(False)
        self.btn_videoClose.setEnabled(False)
        self.warnSpinBox.setEnabled(False)
        self.btn_camera.setEnabled(False)
        self.btn_cameraClose.setEnabled(False)

    # 默认共同步骤处理
    def DefaultCommon(self, fileName):
        # 读取成功与否标志
        flag = False
        try:
            with open(fileName, 'rb') as f:
                self.posList = pickle.load(f)
                # 下一个待添加车位索引标识
                self.nextLabel = len(self.posList) + 1
                flag = True
            self.btn_ableOrEnable(True)
            self.path_parking.setText('车位已选择,可修改')
            pixmap = QPixmap("image/video_car_static.png")
            # 总车位
            self.carPark.setText(str(len(self.posList)))
        except:
            self.btn_ableOrEnable(False)
            self.path_parking.setText("未检测到停车位文件,请先选择")
            pixmap = QPixmap("image/video_car_notSelect.png")
            # 总车位
            self.carPark.setText('0')
        self.lab_video.setPixmap(pixmap)
        # 剩余车位
        self.spaceCarPark.setText('0')
        return flag

    # 默认显示图片
    def Default(self):
        # 非规则车位
        if self.cbtn_parkShape.isChecked():
            self.width_height.setText('非规则形状车位,无需尺寸选择')
            self.DefaultCommon('CarParkPosAbnormal')
        # 规则车位
        else:
            state = self.DefaultCommon('CarParkPos')
            if state:
                self.width_height.setText("横向 : " + str(self.width) + "    纵向 : " + str(self.height) + "   可修改")
            else:
                self.width_height.setText("未检测到车位长宽数据,请先选择")

    # 配置读取 method --->默认0:common  自定义1:custom
    def config(self, method):
        with open('config.json', 'r') as f:
            self.cfg = json.load(f)
            # 车位长宽
            self.width = self.cfg['carCfg']['width']
            self.height = self.cfg['carCfg']['height']
            self.cameraUserPwd = self.cfg['cameraUserPwd']
            self.thresholdSlider.setValue(self.cfg['thresholdCfg'])
            self.thresholdValue.setText(str(self.thresholdSlider.value()))
            method = 'commonCfg' if method == 0 else 'customCfg'
            self.GaussianBlur_ksize = self.cfg[method]['GaussianBlur_ksize']
            self.adaptiveThreshold_blockSize = self.cfg[method]['adaptiveThreshold_blockSize']
            self.adaptiveThreshold_c = self.cfg[method]['adaptiveThreshold_c']
            self.medianBlur_ksize = self.cfg[method]['medianBlur_ksize']
            self.dilate_kernel = self.cfg[method]['dilate_kernel']

    # 使用默认配置
    def commonCfg(self, flag):
        if flag:  # true时 启用播放页面 关闭配置页面 禁用配置保存按钮 读取默认配置
            self.widget_video.setVisible(True)
            self.widget_custom.setVisible(False)
            self.btn_saveCfg.setEnabled(False)
            self.config(0)

    # 自定义配置过程中 禁止除保存配置、切换配置之外的其余所有操作
    def customDeal(self, status):
        self.widget_video.setVisible(status)
        self.btn_wh.setEnabled(status)
        self.btn_parking.setEnabled(status)
        self.btn_video.setEnabled(status)

    # 使用自定义配置
    def customCfg(self, flag):
        if flag:  # true时 关闭播放页面 禁用按钮 启用配置页面 启用配置保存按钮
            self.customDeal(False)
            self.widget_custom.setVisible(True)
            self.btn_saveCfg.setEnabled(True)
            # 调节配置时禁止切换车位形状功能
            self.cbtn_parkShape.setEnabled(False)
            '''自定义配置'''
            # 先获取旧配置同步到滑杆 是个函数
            self.config(1)
            # 是否选定非规则车位
            if self.cbtn_parkShape.isChecked():
                half_minValue = 25
            else:
                # 设置最大值 //整除
                half_minValue = (self.width // 2) if self.width < self.height else (self.height // 2)
            # 保证为奇数
            half_minValue = half_minValue + 1 if half_minValue % 2 == 0 else half_minValue
            # Gau
            self.Gau_Slider.setMaximum(half_minValue)
            self.Gau_Slider.setValue(self.GaussianBlur_ksize)
            # ada_b
            self.ada_b_Slider.setMaximum(half_minValue)
            self.ada_b_Slider.setValue(self.adaptiveThreshold_blockSize)
            # ada_c
            self.ada_c_Slider.setValue(self.adaptiveThreshold_c)
            # med
            self.med_Slider.setMaximum(half_minValue)
            self.med_Slider.setValue(self.medianBlur_ksize)
            # dil
            self.dil_Slider.setValue(self.dilate_kernel)

            # 奇数处理
            def oddHandle(val):
                if val % 2 == 0:
                    return val + 1
                return val

            # 滑杆事件
            def sliderChanged(cus_imgGray):
                # 重新赋值为奇数
                self.Gau_Slider.setValue(oddHandle(self.Gau_Slider.value()))
                self.Gau_value.setText(str(self.Gau_Slider.value()))
                self.ada_b_Slider.setValue(oddHandle(self.ada_b_Slider.value()))
                self.ada_b_value.setText(str(self.ada_b_Slider.value()))
                self.ada_c_value.setText(str(self.ada_c_Slider.value()))
                self.med_Slider.setValue(oddHandle(self.med_Slider.value()))
                self.med_value.setText(str(self.med_Slider.value()))
                self.dil_value.setText(str(self.dil_Slider.value()))

                '''车位图片处理'''
                cus_imgBlur = cv2.GaussianBlur(cus_imgGray, (self.Gau_Slider.value(), self.Gau_Slider.value()), 1)  # 高斯
                cus_imgThreshold = cv2.adaptiveThreshold(cus_imgBlur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                         cv2.THRESH_BINARY_INV,
                                                         self.ada_b_Slider.value(), self.ada_c_Slider.value())
                cus_imgMedian = cv2.medianBlur(cus_imgThreshold, self.med_Slider.value())
                cus_imgDilate = cv2.dilate(cus_imgMedian,
                                           np.ones((self.dil_Slider.value(), self.dil_Slider.value()), np.uint8),
                                           iterations=1)
                cus_imgShow = cv2.cvtColor(cus_imgDilate, cv2.COLOR_BGR2RGB)
                height, width, channels = cus_imgShow.shape
                cus_qImg = QImage(cus_imgShow.data, width, height, width * 3, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(cus_qImg)
                self.cus_lab_video.setPixmap(pixmap.scaled(self.cus_lab_video.size(), Qt.KeepAspectRatio))

            # 图片读取(存在一个小问题 二次往后选择时 会显示上次的图片无法阻止显示)
            try:
                customParking_path = \
                    QFileDialog.getOpenFileName(self, "选择图片文件", "", "图片文件 (*.jpg *.png *.bmp)")[0]
            except:
                customParking_path = ''

            # 成功处理
            if customParking_path:
                c_img = cv2.imread(customParking_path)
                c_imgGray = cv2.cvtColor(c_img, cv2.COLOR_BGR2GRAY)
                # 同步到显示框
                sliderChanged(c_imgGray)
                # 滑杆监听
                self.Gau_Slider.valueChanged.connect(lambda: sliderChanged(c_imgGray))
                self.ada_b_Slider.valueChanged.connect(lambda: sliderChanged(c_imgGray))
                self.ada_c_Slider.valueChanged.connect(lambda: sliderChanged(c_imgGray))
                self.med_Slider.valueChanged.connect(lambda: sliderChanged(c_imgGray))
                self.dil_Slider.valueChanged.connect(lambda: sliderChanged(c_imgGray))
            # 失败处理 --> 使用默认配置
            else:
                self.customDeal(True)
                self.widget_custom.setVisible(False)
                self.btn_saveCfg.setEnabled(False)
                self.cbtn_parkShape.setEnabled(True)
                self.rbtn_commonCfg.setChecked(True)

    # 保存自定义配置 写入json文件
    def saveConfig(self):
        self.cfg['customCfg'] = {
            "GaussianBlur_ksize": self.Gau_Slider.value(),
            "adaptiveThreshold_blockSize": self.ada_b_Slider.value(),
            "adaptiveThreshold_c": self.ada_c_Slider.value(),
            "medianBlur_ksize": self.med_Slider.value(),
            "dilate_kernel": self.dil_Slider.value()
        }
        with open('config.json', 'w') as f:
            json.dump(self.cfg, f, indent=2)
        self.widget_custom.setVisible(False)
        self.btn_saveCfg.setEnabled(False)
        self.cbtn_parkShape.setEnabled(True)
        self.customDeal(True)

    # 车位形状
    def parkShape(self, flag):
        # 非规则
        if flag:
            self.posList = []
            self.temPosList = []
            # 尝试读取车位信息
            try:
                with open('CarParkPosAbnormal', 'rb') as f:
                    self.posList = pickle.load(f)
                    # 下一个待添加车位索引标识
                    self.nextLabel = len(self.posList) + 1
                    self.carPark.setText(str(len(self.posList)))
            except:
                self.nextLabel = 1
                self.btn_ableOrEnable(False)
                self.path_parking.setText('')
                self.carPark.setText('0')
            self.btn_wh.setEnabled(False)
            self.width_height.setText('非规则形状车位,无需尺寸选择')
            self.btn_parking.setEnabled(True)
        # 规则
        else:
            self.posList = []
            try:
                with open('CarParkPos', 'rb') as f:
                    self.posList = pickle.load(f)
                    # 下一个待添加车位索引标识
                    self.nextLabel = len(self.posList) + 1
                    self.carPark.setText(str(len(self.posList)))
                self.btn_ableOrEnable(True)
                self.width_height.setText("横向 : " + str(self.width) + "    纵向 : " + str(self.height) + "   可修改")
                self.path_parking.setText('车位已选择,可修改')
            except:
                self.nextLabel = 1
                self.btn_ableOrEnable(False)
                self.width_height.setText("未检测到车位长宽数据,请先选择")
                self.carPark.setText('0')

            self.btn_wh.setEnabled(True)

    # 车位长宽选定函数
    def process_widthheight(self, parking_path):
        self.tips.setText('鼠标左键选择车位左上角 , 按压拖拽至车位右下角松开绘制出车位区域 , 单击可以重选')
        self.tip_data.setText("已有记录-->横向 : " + str(self.width) + "    纵向 : " + str(self.height))

        def showImage():
            img = cv2.imread(parking_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            height, width, channel = img.shape
            qImg = QImage(img.data, width, height, width * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qImg)
            self.lab_video.setPixmap(pixmap.scaled(self.lab_video.size(), Qt.KeepAspectRatio))
            painter = QPainter(self.lab_video.pixmap())
            painter.setPen(QPen(Qt.red, 2))
            if pos1 != pos2:
                painter.drawRect(pos1[0], pos1[1], pos2[0] - pos1[0], pos2[1] - pos1[1])
            painter.end()

        # 鼠标按下选择车位左上角
        def mousePress(event):
            if not self.is_process_widthheight:
                return
            global pos1, pos2
            pos1 = (event.x(), event.y())

        # 鼠标弹起选择车位右下角
        def mouseRelease(event):
            if not self.is_process_widthheight:
                return
            global pos1, pos2
            pos2 = (event.x(), event.y())
            width = pos2[0] - pos1[0]
            height = pos2[1] - pos1[1]
            self.tip_data.setText("横向 : " + str(width) + "    纵向 : " + str(height))
            if width != 0 and height != 0:
                self.btn_savewh.setEnabled(True)
            else:
                self.btn_savewh.setEnabled(False)
            showImage()

        showImage()
        self.lab_video.mousePressEvent = mousePress
        self.lab_video.mouseReleaseEvent = mouseRelease

    # 车位长宽写入文件
    def saveWidthHeight(self):
        self.width = pos2[0] - pos1[0]
        self.height = pos2[1] - pos1[1]
        self.cfg['carCfg'] = {"width": self.width, "height": self.height}
        with open('./config.json', 'w') as f:
            json.dump(self.cfg, f, indent=2)
        self.btn_savewh.setEnabled(False)
        self.width_height.setText("横向 : " + str(self.width) + "    纵向 : " + str(self.height) + "   可修改")
        self.is_process_widthheight = False
        self.is_process_image = True
        self.is_process_video = False
        # 进入车位处理函数
        self.process_image(self.last_parkingPath)

    # 车位处理函数
    def process_image(self, parking_path):
        self.path_parking.setText(os.path.basename(parking_path))
        self.tip_data.setText("当前选择车位数量 : " + str(len(self.posList)))
        # 车位选择时禁止车位形状选择
        self.cbtn_parkShape.setEnabled(False)
        # 车位选择后禁止视频\摄像头选择
        self.btn_video.setEnabled(False)
        self.btn_camera.setEnabled(False)

        if len(self.posList) != 0:
            self.btn_clearParking.setEnabled(True)
            self.btn_saveParking.setEnabled(True)
        else:
            self.btn_clearParking.setEnabled(False)
            self.btn_saveParking.setEnabled(False)

        # 非规则形状
        if self.cbtn_parkShape.isChecked():
            self.tips.setText("鼠标左键从车位左下角顺时针方向依次点击四角完成车位选择,右键车位区域内可取消当前车位选择")

            # 判断像素是否位于区域内  testPoint为待测点[x,y]  AreaPoint为从左下角按顺时针顺序的4个点[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            def isInterArea(testPoint, AreaPoint):
                LBPoint = [AreaPoint[0].x(), AreaPoint[0].y()]
                LTPoint = [AreaPoint[1].x(), AreaPoint[1].y()]
                RTPoint = [AreaPoint[2].x(), AreaPoint[2].y()]
                RBPoint = [AreaPoint[3].x(), AreaPoint[3].y()]
                a = (LTPoint[0] - LBPoint[0]) * (testPoint[1] - LBPoint[1]) - (LTPoint[1] - LBPoint[1]) * (
                        testPoint[0] - LBPoint[0])
                b = (RTPoint[0] - LTPoint[0]) * (testPoint[1] - LTPoint[1]) - (RTPoint[1] - LTPoint[1]) * (
                        testPoint[0] - LTPoint[0])
                c = (RBPoint[0] - RTPoint[0]) * (testPoint[1] - RTPoint[1]) - (RBPoint[1] - RTPoint[1]) * (
                        testPoint[0] - RTPoint[0])
                d = (LBPoint[0] - RBPoint[0]) * (testPoint[1] - RBPoint[1]) - (LBPoint[1] - RBPoint[1]) * (
                        testPoint[0] - RBPoint[0])
                if (a > 0 and b > 0 and c > 0 and d > 0) or (a < 0 and b < 0 and c < 0 and d < 0):
                    return True
                else:
                    return False

            # 展示图像
            def showImage():
                try:
                    # 读取图片原图显示 opencv读取为BGR色彩空间
                    img = cv2.imread(parking_path)
                    # 转换为RGB色彩空间
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    # shape元组形式(高720、宽1100、通道数3--RGB色彩)
                    height, width, channel = img.shape
                    # 像素级别的操作
                    # QImage(data: Optional[bytes], width: int, height: int, bytesPerLine: int,[原始图片为RGB(R,G,B)类型---3通道,指定bytes型输入数据data在数据排布上的间隔] format: QImage.Format)
                    qImg = QImage(img.data, width, height, width * 3, QImage.Format_RGB888)
                    # 图像级别操作
                    pixmap = QPixmap.fromImage(qImg)
                    # 对图像进行缩放 鼠标点击事件以lable左上角为参考系 Qt.KeepAspectRatio保持原图片的长宽比且不超过label的大小
                    self.lab_video.setPixmap(pixmap.scaled(self.lab_video.size(), Qt.KeepAspectRatio))
                    # 开启绘图功能
                    painter = QPainter(self.lab_video.pixmap())
                    # 设置用于绘制文本的字体
                    font = painter.font()
                    font.setPointSize(15)
                    painter.setFont(font)
                    # 以给定的宽度width和高度height从左上角坐标（x,y）绘制一个矩形
                    for index, (posPointList, posLabel) in enumerate(self.posList):
                        # 设置用于绘制的笔的颜色,大小,样式
                        painter.setPen(QPen(Qt.red, 2))
                        # 绘制不规则图形
                        painter.drawPolygon(QPolygon(posPointList))
                        # 绘制索引值文本
                        painter.setPen(QPen(Qt.green, 2))
                        xMin = min(posPointList[0].x(), posPointList[1].x(), posPointList[2].x(), posPointList[3].x())
                        xMax = max(posPointList[0].x(), posPointList[1].x(), posPointList[2].x(), posPointList[3].x())
                        yMin = min(posPointList[0].y(), posPointList[1].y(), posPointList[2].y(), posPointList[3].y())
                        yMax = max(posPointList[0].y(), posPointList[1].y(), posPointList[2].y(), posPointList[3].y())
                        painter.drawText(xMin + (xMax - xMin) // 2, yMin + (yMax - yMin) // 2, str(posLabel))
                    # 结束绘制操作
                    painter.end()
                except:
                    self.Default()

            # 鼠标事件选择车位
            def mouseClick(event):
                # 视频播放时禁止鼠标事件
                if not self.is_process_image:
                    return
                # 以lable显示框的左上角为起始的x,y对缩放过的图片进行位置选定
                x = event.x()
                y = event.y()
                if event.button() == Qt.LeftButton:
                    self.temPosList.append(QPoint(x, y))
                    # 选定四个坐标
                    if len(self.temPosList) == 4:
                        self.posList.append((self.temPosList, self.nextLabel))
                        self.nextLabel += 1
                        # 当前区域选择完成后清空坐标
                        self.temPosList = []
                        showImage()
                elif event.button() == Qt.RightButton:
                    for i, (posPointList, label) in enumerate(self.posList):
                        # 判断右键的坐标是否在区域内
                        if isInterArea([x, y], posPointList):
                            self.posList.pop(i)
                            break
                    # 对剩余车位信息重新排序
                    for newLabel, (posPointList, posLabel) in enumerate(self.posList, start=1):
                        self.posList[newLabel - 1] = (posPointList, newLabel)
                    # 更新下一个可用的标记值
                    self.nextLabel = len(self.posList) + 1 if self.posList else 1
                    # 刷新显示
                    showImage()
                self.tip_data.setText("当前选择车位数量 : " + str(len(self.posList)))

                if len(self.posList) != 0:
                    self.btn_clearParking.setEnabled(True)
                    self.btn_saveParking.setEnabled(True)
                else:
                    self.btn_clearParking.setEnabled(False)
                    self.btn_saveParking.setEnabled(False)

            showImage()
            self.lab_video.mousePressEvent = mouseClick
        # 规则形状
        else:
            self.tips.setText("鼠标左键点击车位左上角完成车位选择,右键车位区域可取消当前车位选择")

            # 展示图片
            def showImage():
                try:
                    # 读取图片原图显示 opencv读取为BGR色彩空间
                    img = cv2.imread(parking_path)
                    # 转换为RGB色彩空间
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    # shape元组形式(高720、宽1100、通道数3--RGB色彩)
                    height, width, channel = img.shape
                    # 像素级别的操作
                    # QImage(data: Optional[bytes], width: int, height: int, bytesPerLine: int,[原始图片为RGB(R,G,B)类型---3通道,指定bytes型输入数据data在数据排布上的间隔] format: QImage.Format)
                    qImg = QImage(img.data, width, height, width * 3, QImage.Format_RGB888)
                    # 图像级别操作
                    pixmap = QPixmap.fromImage(qImg)
                    # 对图像进行缩放 鼠标点击事件以lable左上角为参考系 Qt.KeepAspectRatio保持原图片的长宽比且不超过label的大小
                    self.lab_video.setPixmap(pixmap.scaled(self.lab_video.size(), Qt.KeepAspectRatio))
                    # 开启绘图功能
                    painter = QPainter(self.lab_video.pixmap())
                    # 设置用于绘制文本的字体
                    font = painter.font()
                    font.setPointSize(15)
                    painter.setFont(font)
                    # 以给定的宽度width和高度height从左上角坐标（x,y）绘制一个矩形
                    for index, (x, y, posLabel) in enumerate(self.posList):
                        # 设置用于绘制的笔的颜色,大小,样式
                        painter.setPen(QPen(Qt.red, 2))
                        # 绘制车位矩形
                        painter.drawRect(x, y, self.width, self.height)
                        # 绘制索引值文本
                        painter.setPen(QPen(Qt.green, 2))
                        painter.drawText(x + self.width // 2, y + self.height // 2, str(posLabel))
                    # 结束绘制操作
                    painter.end()
                except:
                    self.Default()

            # 鼠标事件选择车位
            def mouseClick(event):
                # 视频播放时禁止鼠标事件
                if not self.is_process_image:
                    return
                # 以lable显示框的左上角为起始的x,y对缩放过的图片进行位置选定
                x = event.x()
                y = event.y()
                if event.button() == Qt.LeftButton:
                    self.posList.append((x, y, self.nextLabel))
                    self.nextLabel += 1
                elif event.button() == Qt.RightButton:
                    # 枚举查询是否有当前车位
                    for i, (x1, y1, delLabel) in enumerate(self.posList):
                        if x1 < x < x1 + self.width and y1 < y < y1 + self.height:
                            # 有则删除当前车位
                            self.posList.pop(i)
                            break
                    # 对剩余车位信息重新排序
                    for newLabel, (x, y, _) in enumerate(self.posList, start=1):
                        self.posList[newLabel - 1] = (x, y, newLabel)
                    # 更新下一个可用的标记值
                    self.nextLabel = len(self.posList) + 1 if self.posList else 1
                self.tip_data.setText("当前选择车位数量 : " + str(len(self.posList)))

                if len(self.posList) != 0:
                    self.btn_clearParking.setEnabled(True)
                    self.btn_saveParking.setEnabled(True)
                else:
                    self.btn_clearParking.setEnabled(False)
                    self.btn_saveParking.setEnabled(False)
                showImage()

            showImage()
            self.lab_video.mousePressEvent = mouseClick

    # 停车场车位清空
    def clearParking(self):
        self.posList = []
        self.temPosList = []
        self.btn_clearParking.setEnabled(False)
        self.nextLabel = 1
        if self.cbtn_parkShape.isChecked():
            self.process_image(self.last_parkingPathAb)
        else:
            self.process_image(self.last_parkingPath)

    # 车位保存函数
    def saveParking(self):
        self.is_process_image = False
        # 非规则
        if self.cbtn_parkShape.isChecked():
            with open('CarParkPosAbnormal', 'wb') as f:
                pickle.dump(self.posList, f)
        # 规则
        else:
            with open('CarParkPos', 'wb') as f:
                pickle.dump(self.posList, f)
        self.btn_clearParking.setEnabled(False)
        self.btn_saveParking.setEnabled(False)
        self.path_parking.setText('车位已选择,可修改')
        self.tips.setText('')
        self.tip_data.setText('')
        # 车位保存后启用车位形状选择
        self.cbtn_parkShape.setEnabled(True)
        # 车位保存后启用视频\摄像头选择
        self.btn_video.setEnabled(True)
        self.btn_camera.setEnabled(True)
        # 车位修改完成后检测是否有视频播放记录 若有 调用视频处理
        if self.cbtn_parkShape.isChecked() and self.last_videoPathAb != '':
            self.is_process_widthheight = False
            self.is_process_image = False
            self.is_process_video = True
            self.path_video.setText(os.path.basename(self.last_videoPathAb))
            self.process_video(self.last_videoPathAb, 'v')
        else:
            if (not self.cbtn_parkShape.isChecked()) and self.last_videoPath != '':
                self.is_process_widthheight = False
                self.is_process_image = False
                self.is_process_video = True
                self.path_video.setText(os.path.basename(self.last_videoPath))
                self.process_video(self.last_videoPath, 'v')
            else:
                self.Default()

    # 像素阈值展示
    def thresholdSliderValueChanged(self):
        self.thresholdValue.setText(str(self.thresholdSlider.value()))
        # 值未变化禁用保存按钮
        if self.cfg['thresholdCfg'] != self.thresholdSlider.value():
            self.btn_saveThreshold.setEnabled(True)
        else:
            self.btn_saveThreshold.setEnabled(False)

    # 像素阈值保存
    def saveThresholdSliderValue(self):
        self.cfg['thresholdCfg'] = self.thresholdSlider.value()
        with open('./config.json', 'w') as f:
            json.dump(self.cfg, f, indent=2)
        self.btn_saveThreshold.setEnabled(False)

    # 剩余车位预警开启关闭
    def parkWarning(self, flag):
        if flag:
            self.warnSpinBox.setEnabled(True)
            self.warnSpinBox.setMaximum(len(self.posList))
        else:
            self.warnSpinBox.setEnabled(False)

    # 音频函数
    def audioDeal(self):
        # 判断车位预警是否开启以及是否以及在执行
        if self.cbtn_warning.isChecked() and not self.is_process_audio:
            def playAudio():
                try:
                    playsound('sound/notice.mp3')
                finally:
                    self.is_process_audio = False

            # 剩余车位预警值是否大于剩余车位数量
            if self.warnSpinBox.value() >= self.spaceCarParkCount:
                # 剩余车位数量较少(已使用车位较多) 开启报警
                self.is_process_audio = True
                # 开启副线程执行 防止视频线程卡顿
                threadAudio = threading.Thread(target=playAudio)
                threadAudio.start()
        else:
            return

    # 视频处理函数
    def process_video(self, video_path, med):
        self.tips.setText("视频处理过程中禁止调节配置参数和车位预警数量 可右侧关闭视频后调节")
        # 视频播放时禁用车位尺寸调节
        self.btn_wh.setEnabled(False)
        # 视频播放时禁用车位选择
        self.btn_parking.setEnabled(False)
        # 视频播放时禁用配置调节
        self.rbtn_commonCfg.setEnabled(False)
        self.rbtn_customCfg.setEnabled(False)
        # 视频播放时开启阈值滑杆
        self.thresholdSlider.setEnabled(True)
        # 视频播放时禁止车位预警调节
        self.cbtn_warning.setEnabled(False)
        self.warnSpinBox.setEnabled(False)
        # 视频播放时禁止车位形状选择
        self.cbtn_parkShape.setEnabled(False)
        # 总车位写入页面
        self.carPark.setText(str(len(self.posList)))

        # 判断视频类型
        if med == 'v':
            self.cap = cv2.VideoCapture(video_path)
            self.btn_videoClose.setEnabled(True)
            self.btn_camera.setEnabled(False)
            self.btn_cameraClose.setEnabled(False)
        else:
            self.btn_video.setEnabled(False)
            self.btn_videoClose.setEnabled(False)
            self.btn_cameraClose.setEnabled(True)

        # 停车位检测函数
        def checkParkingSpace(imgPro):
            self.posPointData.clearContents()
            self.posPointData.setRowCount(len(self.posList))
            self.spaceCarParkCount = 0
            # 非规则车位
            if self.cbtn_parkShape.isChecked():
                # 截取车位区域的图像  制作遮罩层
                for inedx, (pos, posLabel) in enumerate(self.posList):
                    mask = np.zeros(imgPro.shape[:2], dtype=np.uint8)
                    posDeal = np.array([[(pos[0].x(), pos[0].y()),
                                         (pos[1].x(), pos[1].y()),
                                         (pos[2].x(), pos[2].y()),
                                         (pos[3].x(), pos[3].y())]], dtype=np.int32)
                    cv2.fillPoly(mask, posDeal, (255))
                    # 计算车位索引显示区域
                    xMin = min(pos[0].x(), pos[1].x(), pos[2].x(), pos[3].x())
                    xMax = max(pos[0].x(), pos[1].x(), pos[2].x(), pos[3].x())
                    yMin = min(pos[0].y(), pos[1].y(), pos[2].y(), pos[3].y())
                    yMax = max(pos[0].y(), pos[1].y(), pos[2].y(), pos[3].y())
                    # 裁剪图片区域(选定车位区域)
                    imgCrop = cv2.bitwise_and(imgPro, mask)
                    # 统计像素点数
                    count = cv2.countNonZero(imgCrop)
                    if count < self.thresholdSlider.value():
                        color = (0, 255, 0)
                        self.posPointData.setItem(self.spaceCarParkCount, 0, QTableWidgetItem(str(posLabel)))
                        self.posPointData.setItem(self.spaceCarParkCount, 1, QTableWidgetItem(str(posDeal[0])))
                        self.spaceCarParkCount += 1
                    else:
                        color = (0, 0, 255)
                    for i in range(4):
                        cv2.line(img=img, pt1=posDeal[0][i], pt2=posDeal[0][(i + 1) % 4], color=color, thickness=2)
                    # 绘制车位索引
                    cvzone.putTextRect(img=img, text=str(posLabel),
                                       pos=(xMin + (xMax - xMin) // 2 - 5, yMin + (yMax - yMin) // 2), scale=1,
                                       thickness=2, offset=0)
                    cvzone.putTextRect(img=img, text=str(count), pos=posDeal[0][0], scale=.8, thickness=2,
                                       colorR=color, offset=0)
            # 规则车位
            else:
                for inedx, (x, y, posLabel) in enumerate(self.posList):
                    # 裁剪图片区域(选定车位区域)
                    imgCrop = imgPro[y:y + self.height, x:x + self.width]
                    # 统计像素点数
                    count = cv2.countNonZero(imgCrop)
                    if count < self.thresholdSlider.value():
                        color = (0, 255, 0)
                        self.posPointData.setItem(self.spaceCarParkCount, 0, QTableWidgetItem(str(posLabel)))
                        self.posPointData.setItem(self.spaceCarParkCount, 1, QTableWidgetItem(str((x,y))))
                        self.spaceCarParkCount += 1
                    else:
                        color = (0, 0, 255)
                    # (图片,长方形框左上角坐标,长方形框右下角坐标,字体颜色,字体粗细)
                    cv2.rectangle(img=img, pt1=(x, y), pt2=(x + self.width, y + self.height), color=color,
                                  thickness=2)
                    # 绘制车位索引
                    cvzone.putTextRect(img=img, text=str(posLabel), pos=(x + self.width // 2 - 5, y + self.height // 2),
                                       scale=1, thickness=2, offset=0)
                    # 车位框显示的像素比较值 (图片,要添加的文字,文字添加到图片上的位置,字体大小,边框粗细,显示框颜色,偏移)
                    cvzone.putTextRect(img=img, text=str(count), pos=(x, y + self.height - 3), scale=.8,
                                       thickness=2, colorR=color, offset=0)

            # 车位数据变化后调用预警函数
            if self.lastSpaceCarParkCount != self.spaceCarParkCount:
                self.audioDeal()
            self.lastSpaceCarParkCount = self.spaceCarParkCount
            self.spaceCarPark.setText(str(self.spaceCarParkCount))

        # 循环检测视频图像帧
        while self.is_process_video:
            success, img = self.cap.read()
            # 调节视频播放分辨率
            if success:
                # 灰度图
                imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                # 高斯模糊 去除噪声 (sigmaX参数不可少)
                imgBlur = cv2.GaussianBlur(imgGray, (self.GaussianBlur_ksize, self.GaussianBlur_ksize), 1)
                # 自定义阈值
                imgThreshold = cv2.adaptiveThreshold(imgBlur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                     cv2.THRESH_BINARY_INV, self.adaptiveThreshold_blockSize,
                                                     self.adaptiveThreshold_c)
                # 中值模糊
                imgMedian = cv2.medianBlur(imgThreshold, self.medianBlur_ksize)
                # 膨胀内核kernel – 进行操作的内核
                kernel = np.ones((self.dilate_kernel, self.dilate_kernel), np.uint8)
                # 膨胀函数                                      ↓膨胀次数iterations
                imgDilate = cv2.dilate(imgMedian, kernel, iterations=1)
                # 调用处理函数函数
                checkParkingSpace(imgDilate)

                height, width, channel = img.shape
                q_image = QImage(img.data, width, height, 3 * width, QImage.Format_RGB888).rgbSwapped()
                # 将图像数据显示在QLabel上
                pixmap = QPixmap.fromImage(q_image)
                self.lab_video.setPixmap(pixmap.scaled(self.lab_video.size(), Qt.KeepAspectRatio))
                # 等待时间为帧率 正常速度播放
                cv2.waitKey(int(self.cap.get(cv2.CAP_PROP_FPS)))
            else:
                # 循环播放
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # 视频\摄像头 关闭共同处理函数
    def closeCommon(self):
        # 停止视频
        self.is_process_video = False
        # 提示建议置空
        self.tips.setText('')
        self.Default()
        # 空闲车位索引和位置清空
        self.posPointData.clearContents()
        # 开启配置调节
        self.rbtn_commonCfg.setEnabled(True)
        self.rbtn_customCfg.setEnabled(True)
        # 视频播放时启用车位尺寸调节
        self.btn_wh.setEnabled(True)
        # 视频播放时启用车位选择
        self.btn_parking.setEnabled(True)
        # 阈值滑杆
        self.thresholdSlider.setEnabled(False)
        # 开启车位预警数量
        self.cbtn_warning.setEnabled(True)
        if self.cbtn_warning.isChecked():
            self.warnSpinBox.setEnabled(True)
        # 开启车位形状选择
        self.cbtn_parkShape.setEnabled(True)

    # 视频关闭处理
    def closeVideo(self):
        # 视频地址置空
        self.path_video.setText('')
        self.closeCommon()

    # 摄像头视频关闭
    def closeCamera(self):
        # 摄像头地址置空
        self.path_camera.setText('')
        self.closeCommon()

    # 停车场车位长宽选择
    def selectWidthHeight(self):
        self.is_process_widthheight = True
        self.is_process_image = False
        self.is_process_video = False
        # 释放视频对象
        if self.cap != '':
            self.cap.release()
        # 预防图片地址获取失败
        try:
            parking_path = QFileDialog.getOpenFileName(self, "选择图片文件", "", "图片文件 (*.jpg *.png *.bmp)")[0]
        except:
            parking_path = ''
        if parking_path:
            # 记录图片地址
            self.last_parkingPath = parking_path
            # 车位长宽选定函数
            self.process_widthheight(parking_path)
        else:
            self.Default()

    # 停车场车位划定选择
    def selectParking(self):
        self.is_process_widthheight = False
        self.is_process_image = True
        self.is_process_video = False
        # 释放视频对象
        if self.cap != '':
            self.cap.release()
        try:
            parking_path = QFileDialog.getOpenFileName(self, "选择图片文件", "", "图片文件 (*.jpg *.png *.bmp)")[0]
        except:
            parking_path = ''
        if parking_path:
            # 非规则\规则车位历史记录
            if self.cbtn_parkShape.isChecked():
                self.last_parkingPathAb = parking_path
            else:
                self.last_parkingPath = parking_path
            # 调用停车车位处理函数
            self.process_image(parking_path)
        else:
            if self.last_parkingPathAb == '' and self.last_parkingPath == '':
                self.Default()
            else:
                if self.cbtn_parkShape.isChecked():
                    parking_path = self.last_parkingPathAb
                else:
                    parking_path = self.last_parkingPath
                # 调用停车车位处理函数
                self.process_image(parking_path)

    # 停车场视频文件选择
    def selectVideo(self):
        self.is_process_widthheight = False
        self.is_process_image = False
        self.is_process_video = True
        # 释放视频对象
        if self.cap != '':
            self.cap.release()
        try:
            video_path = QFileDialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.avi)")[0]
        except:
            video_path = ''
        if video_path:
            # 非规则\规则车位视频历史记录
            if self.cbtn_parkShape.isChecked():
                self.last_videoPathAb = video_path
            else:
                self.last_videoPath = video_path
            # 注意: 若先运行视频函数 地址填充失败 故放在视频函数之前
            self.path_video.setText(os.path.basename(video_path))
            # 调用停车位检测函数
            self.process_video(video_path, 'v')
        else:
            if self.last_videoPathAb == '' and self.last_videoPath == '':
                self.Default()
            else:
                if self.cbtn_parkShape.isChecked():
                    video_path = self.last_videoPathAb
                else:
                    video_path = self.last_videoPath
                self.path_video.setText(os.path.basename(video_path))
                # 调用停车位检测函数
                self.process_video(video_path, 'v')

    # 摄像头ip合法性验证
    def ipAddressValidator(self):
        ipList = self.path_camera.text().split('.')

        # 检验四个字段是否都不为空
        def check_isNull(lst):
            return all(map(lambda x: x != '', lst))

        if check_isNull(ipList):
            # 字符串列表转整数列表判断字段值是否越界
            ipList = list(map(int, ipList))

            # ip字段检测
            def check_isNormal(lst):
                return all(map(lambda x: x > -1 and x < 256, lst))

            # ip地址合法
            if check_isNormal(ipList):
                self.btn_camera.setEnabled(True)
            else:
                self.btn_camera.setEnabled(False)
        else:
            self.btn_camera.setEnabled(False)

    # 停车场摄像头文件选择
    def selectCamera(self):
        self.is_process_widthheight = False
        self.is_process_image = False
        self.is_process_video = True
        # 释放视频对象
        if self.cap != '':
            self.cap.release()
        # icam365摄像头视频流 用户名和密码在配置文件中修改 ip地址系统页面输入
        url = "rtsp://" + self.cameraUserPwd + "@" + self.path_camera.text()
        self.cap = cv2.VideoCapture(url)
        if not self.cap.isOpened():
            print("camera opened failed")
            self.Default()
        else:
            self.btn_camera.setEnabled(False)
            self.process_video('', 'c')


if __name__ == "__main__":
    app = QApplication([])
    myPlayer = videoPlayer()
    myPlayer.center()
    myPlayer.show()
    app.exec()
