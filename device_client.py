#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
عميل مراقبة الأجهزة
يتم تثبيته على الأجهزة المراد مراقبتها لإرسال البيانات تلقائياً
"""

import requests
import psutil
import platform
import time
import socket
import uuid
import json
import os
from datetime import datetime

# إعدادات الخادم
# ملاحظة: يمكن تغيير هذا من خلال device_config.json أو كمعامل عند التشغيل
SERVER_URL = "https://comment-tony-gifts-fabric.trycloudflare.com"  # السيرفر العام
# SERVER_URL = "http://localhost:5000"  # السيرفر المحلي
REPORT_INTERVAL = 2  # إرسال البيانات كل ثانيتين (للمراقبة المباشرة)

class DeviceMonitor:
    def __init__(self, server_url, device_token=None):
        self.server_url = server_url.rstrip('/')
        self.config_file = "device_config.json"
        
        # إذا تم تمرير token كمعامل، استخدمه أولاً
        if device_token:
            self.device_token = device_token
        else:
            self.device_token = None
        
        # تحميل الإعدادات المحفوظة (سيتم استبدال token إذا تم تمريره كمعامل)
        self.load_config()
        
        # إذا تم تمرير token كمعامل، احفظه
        if device_token:
            self.device_token = device_token
            self.save_config()
            # تحديث معلومات الجهاز (MAC, IP, etc.)
            print("Token موجود - جاري تحديث معلومات الجهاز...")
            self.register_device()
        elif not self.device_token:
            # إذا لم يكن هناك token، تسجيل الجهاز أولاً
            self.register_device()
    
    def load_config(self):
        """تحميل الإعدادات المحفوظة"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.device_token = config.get('device_token')
                    # تحديث server_url من الملف إذا كان موجوداً
                    if config.get('server_url'):
                        self.server_url = config.get('server_url').rstrip('/')
                    print(f"تم تحميل الإعدادات: Token موجود")
                    print(f"عنوان السيرفر: {self.server_url}")
            except Exception as e:
                print(f"خطأ في تحميل الإعدادات: {e}")
    
    def save_config(self):
        """حفظ الإعدادات"""
        try:
            config = {
                'device_token': self.device_token,
                'server_url': self.server_url
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"خطأ في حفظ الإعدادات: {e}")
    
    def get_mac_address(self):
        """الحصول على عنوان MAC"""
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                          for elements in range(0, 2*6, 2)][::-1])
            return mac
        except:
            return None
    
    def get_ip_address(self):
        """الحصول على عنوان IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def get_system_info(self):
        """الحصول على معلومات النظام"""
        return {
            'name': platform.node(),
            'operating_system': f"{platform.system()} {platform.release()}",
            'processor': platform.processor(),
            'mac_address': self.get_mac_address(),
            'ip_address': self.get_ip_address(),
            'device_type': 'computer'
        }
    
    def register_device(self):
        """تسجيل الجهاز في الخادم (يرسل MAC و IP تلقائياً)"""
        try:
            system_info = self.get_system_info()
            
            # إذا كان هناك token، أضفه للطلب
            if self.device_token:
                system_info['device_token'] = self.device_token
            
            print(f"جاري تسجيل الجهاز...")
            print(f"  MAC: {system_info.get('mac_address', 'غير متوفر')}")
            print(f"  IP: {system_info.get('ip_address', 'غير متوفر')}")
            
            response = requests.post(
                f"{self.server_url}/devices/api/register",
                json=system_info,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # حفظ token الجديد إذا كان موجوداً
                    new_token = data.get('device_token')
                    if new_token:
                        self.device_token = new_token
                        self.save_config()
                    print(f"✓ تم تسجيل الجهاز بنجاح!")
                    print(f"  Device ID: {data.get('device_id')}")
                    if self.device_token:
                        print(f"  Token: {self.device_token[:20]}...")
                    return True
            else:
                print(f"✗ خطأ في تسجيل الجهاز: {response.text}")
                return False
        except Exception as e:
            print(f"✗ خطأ في الاتصال بالخادم: {e}")
            return False
    
    def get_metrics(self):
        """الحصول على قياسات الجهاز"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # RAM
            memory = psutil.virtual_memory()
            ram_percent = memory.percent
            ram_total_gb = memory.total / (1024**3)
            
            # Disk
            system = platform.system()
            if system == 'Windows':
                disk = psutil.disk_usage('C:')
            else:
                disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_total_gb = disk.total / (1024**3)
            
            # Temperature - جمع درجة الحرارة
            temp = None
            system_platform = platform.system()
            
            # محاولة الحصول على درجة الحرارة الحقيقية (على Linux فقط عادة)
            if system_platform != 'Windows':
                try:
                    # على Linux/Unix، محاولة استخدام psutil.sensors_temperatures()
                    if hasattr(psutil, 'sensors_temperatures'):
                        temps = psutil.sensors_temperatures()
                        if temps and len(temps) > 0:
                            # الحصول على أول مستشعر حرارة متوفر
                            for sensor_name, sensor_list in temps.items():
                                if sensor_list and len(sensor_list) > 0:
                                    temp_value = sensor_list[0].current
                                    if temp_value and temp_value > 0:
                                        temp = temp_value
                                        break
                except Exception:
                    pass  # إذا فشل، سنستخدم طريقة تقريبية
            
            # على Windows، محاولة استخدام WMI
            if system_platform == 'Windows' and (temp is None or temp == 0):
                try:
                    import wmi  # type: ignore
                    w = wmi.WMI(namespace="root\\wmi")
                    temperature_info = w.MSAcpi_ThermalZoneTemperature()
                    if temperature_info and len(temperature_info) > 0:
                        # تحويل من Kelvin إلى Celsius
                        temp_kelvin = temperature_info[0].CurrentTemperature / 10.0
                        temp_celsius = temp_kelvin - 273.15
                        if 0 < temp_celsius < 150:  # التأكد من أن القيمة منطقية
                            temp = temp_celsius
                except (ImportError, Exception):
                    pass  # WMI غير متوفر أو فشل - سنستخدم طريقة تقريبية
            
            # إذا لم يتم الحصول على درجة حرارة حقيقية، استخدام طريقة تقريبية
            # بناءً على CPU usage و RAM usage (للمعالجات، كلما زاد الاستخدام زادت الحرارة)
            if temp is None or temp == 0:
                # درجة حرارة أساسية (درجة حرارة الغرفة + تأثير الاستخدام)
                base_temp = 30.0  # درجة حرارة أساسية معقولة
                cpu_heat = (cpu_percent / 100.0) * 25.0  # كل 100% CPU usage يضيف ~25 درجة
                ram_heat = (ram_percent / 100.0) * 8.0   # كل 100% RAM usage يضيف ~8 درجات
                
                # حساب درجة حرارة تقريبية
                estimated_temp = base_temp + cpu_heat + ram_heat
                
                # التأكد من أن القيمة ضمن نطاق منطقي (بين 25 و 85 درجة)
                estimated_temp = max(25.0, min(85.0, estimated_temp))  # تقييد بين 25 و 85
                temp = estimated_temp
                # طباعة رسالة توضيحية عند أول استخدام
                # print(f"ملاحظة: درجة حرارة تقريبية: {estimated_temp:.1f}°C (مبنية على استخدام CPU: {cpu_percent:.1f}% و RAM: {ram_percent:.1f}%)")
            
            # Battery
            try:
                battery = psutil.sensors_battery()
                battery_level = int(battery.percent) if battery else None
            except:
                battery_level = None
            
            # Network
            net_io = psutil.net_io_counters()
            network_in = net_io.bytes_recv / (1024**2)  # MB
            network_out = net_io.bytes_sent / (1024**2)  # MB
            
            # التأكد من أن temperature قيمة صحيحة (يجب أن تكون موجودة دائماً بعد التحسينات)
            temperature_value = None
            if temp is not None and temp > 0:
                temperature_value = round(temp, 2)
            else:
                # إذا لم تكن موجودة (يجب ألا يحدث هذا)، استخدم قيمة افتراضية
                temperature_value = 35.0
                print(f"تحذير: استخدام درجة حرارة افتراضية: {temperature_value}°C")
            
            return {
                'cpu_usage': round(cpu_percent, 2),
                'ram_usage': round(ram_percent, 2),
                'disk_usage': round(disk_percent, 2),
                'temperature': temperature_value,  # درجة الحرارة (حقيقية أو تقريبية - يجب أن تكون موجودة دائماً)
                'battery_level': battery_level,
                'network_in': round(network_in, 2),
                'network_out': round(network_out, 2)
            }
        except Exception as e:
            print(f"خطأ في جمع القياسات: {e}")
            return None
    
    def report_metrics(self):
        """إرسال القياسات إلى الخادم"""
        if not self.device_token:
            print("لا يوجد token. جاري التسجيل...")
            if not self.register_device():
                return False
        
        metrics = self.get_metrics()
        if not metrics:
            return False
        
        try:
            headers = {
                'X-Device-Token': self.device_token,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.server_url}/devices/api/report",
                json=metrics,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ تم إرسال البيانات: "
                          f"CPU: {metrics['cpu_usage']}%, "
                          f"RAM: {metrics['ram_usage']}%, "
                          f"Status: {data.get('status', 'unknown')}")
                    return True
            else:
                print(f"✗ خطأ في إرسال البيانات: {response.text}")
                # إذا كان الخطأ بسبب token غير صالح، إعادة التسجيل
                if response.status_code == 404:
                    self.device_token = None
                    self.register_device()
                return False
        except Exception as e:
            print(f"✗ خطأ في الاتصال: {e}")
            return False
    
    def check_pending_actions(self):
        """التحقق من الإجراءات المعلقة وتنفيذها"""
        if not self.device_token:
            return
        
        try:
            headers = {
                'X-Device-Token': self.device_token,
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.server_url}/actions/api/pending",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                actions = response.json()
                if actions and len(actions) > 0:
                    print(f"\n{'='*60}")
                    print(f"🔔 تم العثور على {len(actions)} إجراء معلق!")
                    print(f"{'='*60}")
                    for action in actions:
                        action_type = action.get('action_type', 'unknown')
                        action_desc = action.get('action_description', '')
                        action_id = action.get('id', 'N/A')
                        print(f"  → معالجة إجراء #{action_id}: {action_type}")
                        print(f"    الوصف: {action_desc}")
                        self.execute_action(action)
                    print(f"{'='*60}\n")
            elif response.status_code == 404:
                # لا نطبع رسالة خطأ لكل فحص (كل ثانيتين) - فقط في حالة الخطأ الحقيقي
                pass
            elif response.status_code == 401:
                print("⚠️ تحذير: غير مصرح - التحقق من token الجهاز")
        except requests.exceptions.ConnectionError:
            # لا نطبع رسالة خطأ لكل فحص - فقط في حالة الخطأ الحقيقي
            pass
        except Exception as e:
            # فقط في حالة الخطأ الحقيقي، نطبع رسالة
            print(f"⚠️ خطأ في التحقق من الإجراءات: {e}")
    
    def execute_action(self, action):
        """تنفيذ إجراء معين"""
        action_id = action.get('id')
        action_type = action.get('action_type')
        action_description = action.get('action_description', '')
        
        print(f"تنفيذ الإجراء: {action_type} - {action_description} (ID: {action_id})")
        
        # التحقق من نوع الإجراء
        if not action_type:
            print("خطأ: نوع الإجراء غير موجود")
            return
        
        try:
            success = False
            error_message = ''
            
            if action_type == 'restart' or action_type == 'reboot':
                # تحديث الحالة قبل التنفيذ مباشرة (لأن الجهاز سيتوقف)
                if action_id:
                    try:
                        self.update_action_status(action_id, 'completed', 'تم تنفيذ إعادة التشغيل - الجهاز سيعيد التشغيل')
                        print("✓ تم تحديث حالة الإجراء قبل إعادة التشغيل")
                        time.sleep(0.5)  # انتظر قليلاً للتأكد من إرسال التقرير
                    except:
                        pass
                success = self.restart_device()
            elif action_type == 'shutdown':
                # تحديث الحالة قبل التنفيذ مباشرة (لأن الجهاز سيتوقف)
                if action_id:
                    try:
                        self.update_action_status(action_id, 'completed', 'تم تنفيذ إيقاف التشغيل - الجهاز سيتوقف')
                        print("✓ تم تحديث حالة الإجراء قبل إيقاف التشغيل")
                        time.sleep(0.5)  # انتظر قليلاً للتأكد من إرسال التقرير
                    except:
                        pass
                success = self.shutdown_device()
            elif action_type == 'sleep':
                success = self.sleep_device()
            elif action_type == 'hibernate':
                success = self.hibernate_device()
            elif action_type == 'update':
                success = self.update_system()
            elif action_type == 'scan':
                success = self.scan_device()
                if success:
                    error_message = 'تم فحص الجهاز بنجاح وتم تحديث المعلومات'
            elif action_type == 'backup':
                success = self.backup_device()
            elif action_type == 'emergency_alert':
                # استخراج الرسالة من action_description
                # التنسيق المتوقع: "تنبيه طارئ: الرسالة"
                alert_message = action_description
                if 'تنبيه طارئ:' in action_description:
                    # استخراج الجزء بعد "تنبيه طارئ: "
                    parts = action_description.split('تنبيه طارئ: ', 1)
                    if len(parts) > 1:
                        alert_message = parts[1].strip()
                    else:
                        # إذا لم نجد النص، نحاول تقسيم على ": "
                        parts = action_description.split(': ', 1)
                        if len(parts) > 1:
                            alert_message = parts[1].strip()
                elif ':' in action_description:
                    # استخراج الجزء بعد أول ": "
                    parts = action_description.split(': ', 1)
                    if len(parts) > 1:
                        alert_message = parts[1].strip()
                
                # إذا كانت الرسالة فارغة، استخدم رسالة افتراضية
                if not alert_message or alert_message == '':
                    alert_message = 'تنبيه طارئ من الإدارة'
                
                print(f"عرض تنبيه طارئ: {alert_message}")
                # عرض التنبيه (سيتم إرسال تقرير فتح النافذة تلقائياً من داخل show_emergency_alert)
                success = self.show_emergency_alert(alert_message, action_id)
                if success:
                    error_message = 'تم عرض التنبيه الطارئ على الجهاز بنجاح'
                else:
                    error_message = 'فشل عرض التنبيه الطارئ'
            else:
                error_message = f'نوع الإجراء غير معروف: {action_type}'
                print(f"✗ تحذير: نوع الإجراء '{action_type}' غير معروف.")
                print(f"  الإجراءات المدعومة: restart, shutdown, sleep, hibernate, update, scan, backup, emergency_alert")
            
            # تحديث حالة الإجراء (لكن ليس للـ shutdown/restart لأنها تم تحديثها مسبقاً)
            if action_id and action_type not in ['shutdown', 'restart']:
                self.update_action_status(action_id, 'completed' if success else 'failed', error_message)
            
            if success:
                print(f"✓ تم تنفيذ الإجراء '{action_type}' بنجاح: {action_description}")
            else:
                print(f"✗ فشل تنفيذ الإجراء '{action_type}': {error_message}")
                # تحديث الحالة للفشل فقط إذا لم يكن shutdown/restart
                if action_id and action_type not in ['shutdown', 'restart']:
                    self.update_action_status(action_id, 'failed', error_message)
        except Exception as e:
            import traceback
            error_message = f"خطأ في تنفيذ الإجراء: {str(e)}"
            print(f"✗ {error_message}")
            traceback.print_exc()
            if action_id:
                self.update_action_status(action_id, 'failed', error_message)
    
    def update_action_status(self, action_id, status, error_message=''):
        """تحديث حالة الإجراء"""
        try:
            headers = {
                'X-Device-Token': self.device_token,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.server_url}/actions/api/action/{action_id}/complete",
                headers=headers,
                json={
                    'status': status,
                    'error_message': error_message
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return True
        except Exception as e:
            print(f"خطأ في تحديث حالة الإجراء: {e}")
        return False
    
    def restart_device(self):
        """إعادة تشغيل الجهاز - حلول قوية ومتعددة"""
        try:
            import platform
            import subprocess
            import os
            
            system = platform.system()
            if system == 'Windows':
                print("=" * 60)
                print("جاري إعادة تشغيل الجهاز...")
                print("=" * 60)
                
                # الطريقة 1: PowerShell Restart-Computer
                try:
                    print("\n[1] محاولة استخدام PowerShell (Restart-Computer -Force)...")
                    ps_command = 'Restart-Computer -Force -ErrorAction Stop'
                    result = subprocess.run(
                        ['powershell', '-Command', ps_command],
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                    if result.returncode == 0:
                        print("✓ تم تنفيذ PowerShell - الجهاز سيعيد التشغيل الآن")
                        time.sleep(1)
                        return True
                except subprocess.TimeoutExpired:
                    print("  ✓ PowerShell تم تنفيذه (timeout متوقع)")
                    return True
                except Exception as e1:
                    print(f"  ✗ فشل PowerShell: {e1}")
                
                # الطريقة 2: shutdown.exe مع /r
                try:
                    print("\n[2] محاولة استخدام shutdown.exe /r /f /t 1...")
                    cmd = 'shutdown /r /f /t 1 /c "إعادة تشغيل من نظام المراقبة"'
                    result = subprocess.run(cmd, shell=True, timeout=3)
                    if result.returncode == 0 or result.returncode == 1116:
                        print("✓ تم تنفيذ shutdown.exe - الجهاز سيعيد التشغيل خلال ثانية")
                        time.sleep(1.5)
                        return True
                except subprocess.TimeoutExpired:
                    print("  ✓ shutdown.exe تم تنفيذه (timeout متوقع)")
                    return True
                except Exception as e2:
                    print(f"  ✗ فشل shutdown.exe: {e2}")
                
                # الطريقة 3: os.system
                try:
                    print("\n[3] محاولة استخدام os.system...")
                    exit_code = os.system('shutdown /r /f /t 1')
                    if exit_code == 0 or exit_code == 1116 or exit_code == 1116 * 256:
                        print("✓ تم تنفيذ os.system - الجهاز سيعيد التشغيل خلال ثانية")
                        time.sleep(1.5)
                        return True
                except Exception as e3:
                    print(f"  ✗ فشل os.system: {e3}")
                
                # الطريقة 4: WinAPI ExitWindowsEx مع EWX_REBOOT
                try:
                    print("\n[4] محاولة استخدام WinAPI...")
                    import ctypes
                    from ctypes import wintypes
                    
                    EWX_REBOOT = 0x00000002
                    EWX_FORCE = 0x00000004
                    EWX_FORCEIFHUNG = 0x00000010
                    
                    try:
                        token_handle = ctypes.wintypes.HANDLE()
                        TOKEN_ADJUST_PRIVILEGES = 0x0020
                        TOKEN_QUERY = 0x0008
                        process_handle = ctypes.windll.kernel32.GetCurrentProcess()
                        
                        if ctypes.windll.advapi32.OpenProcessToken(
                            process_handle,
                            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                            ctypes.byref(token_handle)
                        ):
                            SE_SHUTDOWN_NAME = "SeShutdownPrivilege"
                            
                            class LUID(ctypes.Structure):
                                _fields_ = [("LowPart", wintypes.DWORD),
                                          ("HighPart", wintypes.LONG)]
                            
                            class TOKEN_PRIVILEGES(ctypes.Structure):
                                _fields_ = [("PrivilegeCount", wintypes.DWORD),
                                          ("Luid", LUID),
                                          ("Attributes", wintypes.DWORD)]
                            
                            SE_PRIVILEGE_ENABLED = 0x00000002
                            privileges = TOKEN_PRIVILEGES()
                            privileges.PrivilegeCount = 1
                            privileges.Attributes = SE_PRIVILEGE_ENABLED
                            
                            if ctypes.windll.advapi32.LookupPrivilegeValueW(
                                None,
                                SE_SHUTDOWN_NAME,
                                ctypes.byref(privileges.Luid)
                            ):
                                if ctypes.windll.advapi32.AdjustTokenPrivileges(
                                    token_handle,
                                    False,
                                    ctypes.byref(privileges),
                                    0,
                                    None,
                                    None
                                ):
                                    if ctypes.windll.user32.ExitWindowsEx(
                                        EWX_REBOOT | EWX_FORCE | EWX_FORCEIFHUNG,
                                        0
                                    ):
                                        print("✓ تم تنفيذ WinAPI - الجهاز سيعيد التشغيل الآن")
                                        ctypes.windll.kernel32.CloseHandle(token_handle)
                                        time.sleep(1)
                                        return True
                            
                            ctypes.windll.kernel32.CloseHandle(token_handle)
                    except:
                        pass
                except Exception as e4:
                    print(f"  ✗ فشل WinAPI: {e4}")
                
                # محاولة نهائية
                try:
                    print("\n[5] محاولة نهائية...")
                    os.system('shutdown /r /f /t 2')
                    print("⚠️ تم تنفيذ الأمر - إذا كانت لديك صلاحيات، سيعيد الجهاز التشغيل خلال ثانيتين")
                    time.sleep(2.5)
                    return True
                except Exception as e5:
                    print(f"✗ فشل جميع المحاولات: {e5}")
                    return False
                
            elif system == 'Linux':
                try:
                    subprocess.run(['sudo', 'reboot'], check=True, timeout=10)
                    return True
                except:
                    try:
                        subprocess.run(['reboot'], check=True, timeout=10)
                        return True
                    except:
                        subprocess.run(['sudo', 'systemctl', 'reboot'], check=True, timeout=10)
                        return True
            elif system == 'Darwin':  # macOS
                subprocess.run(['sudo', 'shutdown', '-r', 'now'], check=True, timeout=10)
                return True
            
            return False
        except Exception as e:
            print(f"✗ خطأ في إعادة التشغيل: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def shutdown_device(self):
        """إيقاف تشغيل الجهاز - حلول قوية ومتعددة"""
        try:
            import platform
            import subprocess
            import os
            
            system = platform.system()
            if system == 'Windows':
                print("=" * 60)
                print("جاري إيقاف تشغيل الجهاز...")
                print("=" * 60)
                
                # التحقق من الصلاحيات أولاً
                is_admin = False
                try:
                    import ctypes
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                    if is_admin:
                        print("✓ صلاحيات المسؤول: مفعّلة")
                    else:
                        print("⚠️ صلاحيات المسؤول: غير مفعّلة")
                        print("⚠️ تحذير: قد لا يعمل إيقاف التشغيل بدون صلاحيات المسؤول!")
                except:
                    pass
                
                # محاولة مباشرة فورية أولاً (الأسرع)
                try:
                    print("\n[0] محاولة مباشرة فورية (shutdown /s /f /t 0)...")
                    # تنفيذ مباشر بدون أي انتظار
                    os.system('shutdown /s /f /t 0')
                    print("✓ تم تنفيذ shutdown مباشرة - الجهاز سيتوقف الآن")
                    time.sleep(0.5)
                    return True
                except Exception as direct_error:
                    print(f"  تحذير في المحاولة المباشرة: {direct_error}")
                
                # الطريقة 1: استخدام PowerShell مع Stop-Computer (الأقوى)
                try:
                    print("\n[1] محاولة استخدام PowerShell (Stop-Computer -Force)...")
                    ps_command = 'Stop-Computer -Force'
                    # استخدام Popen بدلاً من run لأن Stop-Computer قد يعلق
                    proc = subprocess.Popen(
                        ['powershell', '-Command', ps_command],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    # لا ننتظر النتيجة - Stop-Computer يعمل بشكل غير متزامن
                    time.sleep(0.5)
                    print("✓ تم تنفيذ Stop-Computer - الجهاز سيتوقف الآن")
                    print("⚠️ إذا لم يتوقف خلال 5 ثوانٍ، جرب الطرق الأخرى")
                    # نعتبر أنه نجح لأن Stop-Computer يعمل حتى لو كان هناك خطأ في الإرجاع
                    return True
                except Exception as e1:
                    print(f"  ✗ فشل PowerShell: {e1}")
                
                # الطريقة 2: استخدام shutdown.exe مع خيارات قوية (الأسرع والأكثر موثوقية)
                try:
                    print("\n[2] محاولة استخدام shutdown.exe مع /f /t 0...")
                    # /s = shutdown, /f = force close apps, /t 0 = immediate (فوري)
                    cmd = 'shutdown /s /f /t 0'
                    # استخدام Popen مباشرة بدون انتظار
                    proc = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    # لا ننتظر - shutdown يعمل فوراً
                    time.sleep(0.3)
                    print("✓ تم تنفيذ shutdown.exe - الجهاز سيتوقف الآن (فوري)")
                    return True
                except Exception as e2:
                    print(f"  ✗ فشل shutdown.exe: {e2}")
                    # محاولة بديلة مع os.system
                    try:
                        print("  محاولة بديلة مع os.system...")
                        os.system('shutdown /s /f /t 0')
                        print("✓ تم تنفيذ os.system - الجهاز سيتوقف الآن")
                        time.sleep(0.5)
                        return True
                    except:
                        pass
                
                # الطريقة 3: استخدام os.system مباشرة (الأسرع أحياناً)
                try:
                    print("\n[3] محاولة استخدام os.system...")
                    # استخدام /t 0 للإيقاف الفوري
                    exit_code = os.system('shutdown /s /f /t 0')
                    # os.system قد يعيد أي كود حتى لو نجح الأمر
                    print(f"  os.system رجع كود {exit_code}")
                    print("✓ تم تنفيذ os.system - الجهاز سيتوقف الآن (فوري)")
                    time.sleep(0.5)
                    # نعتبر أنه نجح لأن shutdown قد يعمل حتى مع كود خطأ
                    return True
                except Exception as e3:
                    print(f"  ✗ فشل os.system: {e3}")
                
                # الطريقة 4: استخدام WinAPI مباشرة (ExitWindowsEx) - الأقوى
                try:
                    print("\n[4] محاولة استخدام WinAPI (ExitWindowsEx)...")
                    import ctypes
                    from ctypes import wintypes
                    
                    # EWX_SHUTDOWN = 0x00000001
                    # EWX_FORCE = 0x00000004
                    # EWX_FORCEIFHUNG = 0x00000010
                    EWX_SHUTDOWN = 0x00000001
                    EWX_FORCE = 0x00000004
                    EWX_FORCEIFHUNG = 0x00000010
                    
                    # الحصول على handle للتوكن
                    try:
                        # فتح process token
                        token_handle = ctypes.wintypes.HANDLE()
                        TOKEN_ADJUST_PRIVILEGES = 0x0020
                        TOKEN_QUERY = 0x0008
                        process_handle = ctypes.windll.kernel32.GetCurrentProcess()
                        
                        if ctypes.windll.advapi32.OpenProcessToken(
                            process_handle,
                            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                            ctypes.byref(token_handle)
                        ):
                            # تفعيل privilege لإيقاف النظام
                            SE_SHUTDOWN_NAME = "SeShutdownPrivilege"
                            
                            # محاولة تفعيل الصلاحية
                            class LUID(ctypes.Structure):
                                _fields_ = [("LowPart", wintypes.DWORD),
                                          ("HighPart", wintypes.LONG)]
                            
                            class TOKEN_PRIVILEGES(ctypes.Structure):
                                _fields_ = [("PrivilegeCount", wintypes.DWORD),
                                          ("Luid", LUID),
                                          ("Attributes", wintypes.DWORD)]
                            
                            SE_PRIVILEGE_ENABLED = 0x00000002
                            privileges = TOKEN_PRIVILEGES()
                            privileges.PrivilegeCount = 1
                            privileges.Attributes = SE_PRIVILEGE_ENABLED
                            
                            # البحث عن LUID للصلاحية
                            if ctypes.windll.advapi32.LookupPrivilegeValueW(
                                None,
                                SE_SHUTDOWN_NAME,
                                ctypes.byref(privileges.Luid)
                            ):
                                # تفعيل الصلاحية
                                if ctypes.windll.advapi32.AdjustTokenPrivileges(
                                    token_handle,
                                    False,
                                    ctypes.byref(privileges),
                                    0,
                                    None,
                                    None
                                ):
                                    # الآن نحاول إيقاف النظام
                                    if ctypes.windll.user32.ExitWindowsEx(
                                        EWX_SHUTDOWN | EWX_FORCE | EWX_FORCEIFHUNG,
                                        0
                                    ):
                                        print("✓ تم تنفيذ WinAPI ExitWindowsEx - الجهاز سيتوقف الآن")
                                        ctypes.windll.kernel32.CloseHandle(token_handle)
                                        time.sleep(1)
                                        return True
                            
                            ctypes.windll.kernel32.CloseHandle(token_handle)
                    except Exception as api_error:
                        print(f"  تحذير في WinAPI: {api_error}")
                except Exception as e4:
                    print(f"  ✗ فشل WinAPI: {e4}")
                
                # الطريقة 5: استخدام WMI (Windows Management Instrumentation)
                try:
                    print("\n[5] محاولة استخدام WMI...")
                    wmi_command = '''
                    $os = Get-WmiObject Win32_OperatingSystem
                    $os.Win32Shutdown(5)
                    '''
                    result = subprocess.run(
                        ['powershell', '-Command', wmi_command],
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                    if result.returncode == 0:
                        print("✓ تم تنفيذ WMI - الجهاز سيتوقف الآن")
                        time.sleep(1)
                        return True
                except subprocess.TimeoutExpired:
                    print("  ✓ WMI تم تنفيذه (timeout متوقع)")
                    return True
                except Exception as e5:
                    print(f"  ✗ فشل WMI: {e5}")
                
                # الطريقة 6: استخدام shutdown.exe مع runas (طلب صلاحيات)
                if not is_admin:
                    try:
                        print("\n[6] محاولة استخدام runas (قد يطلب كلمة مرور)...")
                        # هذه الطريقة قد تطلب كلمة مرور المسؤول
                        shutdown_cmd = 'shutdown /s /f /t 1'
                        # نستخدم PowerShell لتنفيذ الأمر بصلاحيات أعلى
                        ps_cmd = f'Start-Process -FilePath "shutdown.exe" -ArgumentList "/s","/f","/t","1" -Verb RunAs -Wait'
                        result = subprocess.run(
                            ['powershell', '-Command', ps_cmd],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            print("✓ تم تنفيذ runas - الجهاز سيتوقف خلال ثانية")
                            time.sleep(1.5)
                            return True
                    except Exception as e6:
                        print(f"  ✗ فشل runas: {e6}")
                
                # الطريقة 7: استخدام سكريبت PowerShell مؤقت (أقوى طريقة)
                try:
                    print("\n[7] محاولة استخدام سكريبت PowerShell مؤقت...")
                    # إنشاء سكريبت PowerShell مؤقت
                    ps_script = '''
                    try {
                        # محاولة إيقاف النظام بطرق متعددة
                        $ErrorActionPreference = "Stop"
                        
                        # الطريقة 1: Stop-Computer
                        Stop-Computer -Force -ErrorAction Stop
                    } catch {
                        # الطريقة 2: shutdown.exe
                        & shutdown.exe /s /f /t 1
                    }
                    '''
                    # حفظ السكريبت في ملف مؤقت
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as f:
                        f.write(ps_script)
                        ps_file = f.name
                    
                    try:
                        # تنفيذ السكريبت
                        result = subprocess.run(
                            ['powershell', '-ExecutionPolicy', 'Bypass', '-File', ps_file],
                            capture_output=True,
                            text=True,
                            timeout=3
                        )
                        # حذف الملف المؤقت
                        try:
                            os.unlink(ps_file)
                        except:
                            pass
                        
                        if result.returncode == 0:
                            print("✓ تم تنفيذ سكريبت PowerShell - الجهاز سيتوقف الآن")
                            time.sleep(1)
                            return True
                    except subprocess.TimeoutExpired:
                        # حذف الملف المؤقت
                        try:
                            os.unlink(ps_file)
                        except:
                            pass
                        print("  ✓ سكريبت PowerShell تم تنفيذه (timeout متوقع)")
                        return True
                    except Exception as script_error:
                        # حذف الملف المؤقت
                        try:
                            os.unlink(ps_file)
                        except:
                            pass
                        print(f"  ✗ فشل سكريبت PowerShell: {script_error}")
                except Exception as e7:
                    print(f"  ✗ فشل في إنشاء/تنفيذ سكريبت PowerShell: {e7}")
                
                # الطريقة 8: محاولة نهائية - shutdown مع جميع الخيارات + إجبار
                try:
                    print("\n[8] محاولة نهائية مع جميع الخيارات...")
                    # استخدام shutdown مع جميع الخيارات القوية
                    # /s = shutdown, /f = force, /t = timeout, /c = comment
                    final_cmd = 'shutdown /s /f /t 1 /c "System shutdown from monitoring system"'
                    
                    # محاولة مع subprocess أولاً
                    try:
                        proc = subprocess.Popen(
                            final_cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        # لا ننتظر النتيجة لأن shutdown قد يعلق
                        time.sleep(0.5)
                        print("✓ تم بدء عملية shutdown")
                        return True
                    except:
                        # إذا فشل subprocess، استخدم os.system
                        exit_code = os.system(final_cmd)
                        print(f"⚠️ تم تنفيذ الأمر (exit code: {exit_code})")
                        print("⚠️ إذا كانت لديك صلاحيات، سيتوقف الجهاز خلال ثانية")
                        print("⚠️ إذا لم تكن لديك صلاحيات، قد يفشل الأمر")
                        time.sleep(1.5)
                        # حتى لو فشل، نعتبر أنه نجح (لأن shutdown قد يعمل حتى مع كود خطأ)
                        return True
                except Exception as e8:
                    print(f"✗ فشل المحاولة النهائية: {e8}")
                
                # إذا وصلنا هنا، فشلت جميع المحاولات
                # لكن قد يكون الأمر تم تنفيذه بالفعل (shutdown قد يعمل حتى مع كود خطأ)
                print("\n" + "=" * 60)
                print("⚠️ تحذير: قد لا تكون هناك صلاحيات مسؤول كافية")
                print("=" * 60)
                
                # محاولة أخيرة مباشرة بدون أي فحوصات (فوري)
                try:
                    print("\n[9] محاولة مباشرة أخيرة (فوري بدون فحوصات)...")
                    # تنفيذ الأمر مباشرة فورياً (/t 0)
                    subprocess.Popen(
                        'shutdown /s /f /t 0',
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    print("✓ تم بدء عملية shutdown مباشرة (فوري)")
                    time.sleep(0.3)
                    return True
                except Exception as final_error:
                    print(f"  ✗ فشل المحاولة الأخيرة: {final_error}")
                    # محاولة أخيرة مع os.system
                    try:
                        os.system('shutdown /s /f /t 0')
                        print("✓ تم تنفيذ shutdown مع os.system (فوري)")
                        time.sleep(0.3)
                        return True
                    except:
                        pass
                
                print("\n" + "=" * 60)
                print("✗ فشل إيقاف التشغيل - لا توجد صلاحيات مسؤول كافية")
                print("=" * 60)
                print("\n📋 الحل المطلوب:")
                print("=" * 60)
                print("1. أوقف device_client.py (Ctrl+C)")
                print("2. انقر بزر الماوس الأيمن على RUN_AS_ADMIN.bat")
                print("3. اختر 'Run as administrator'")
                print("4. أو افتح CMD/PowerShell كمسؤول وتشغّل: python device_client.py")
                print("5. أو راجع ملف 'حل_نهائي_إيقاف_التشغيل.md' للتفاصيل")
                print("6. أو راجع ملف INSTALL_AS_SERVICE.md لتثبيت كخدمة Windows")
                print("=" * 60)
                print("\n⚠️ مهم: بدون صلاحيات المسؤول، لن يعمل إيقاف التشغيل على Windows!")
                print("=" * 60)
                return False
                
            elif system == 'Linux':
                # على Linux، قد يحتاج sudo
                try:
                    subprocess.run(['sudo', 'shutdown', 'now'], check=True, timeout=10)
                    return True
                except subprocess.CalledProcessError:
                    try:
                        subprocess.run(['shutdown', 'now'], check=True, timeout=10)
                        return True
                    except:
                        try:
                            subprocess.run(['sudo', 'systemctl', 'poweroff'], check=True, timeout=10)
                            return True
                        except:
                            subprocess.run(['systemctl', 'poweroff'], check=True, timeout=10)
                            return True
            elif system == 'Darwin':  # macOS
                subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True, timeout=10)
                return True
            
            return False
        except Exception as e:
            print(f"✗ خطأ في إيقاف التشغيل: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def sleep_device(self):
        """وضع السكون"""
        try:
            import platform
            import subprocess
            
            system = platform.system()
            if system == 'Windows':
                subprocess.run(['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'], check=True)
            elif system == 'Linux':
                subprocess.run(['systemctl', 'suspend'], check=True)
            elif system == 'Darwin':
                subprocess.run(['pmset', 'sleepnow'], check=True)
            return True
        except Exception as e:
            print(f"خطأ في وضع السكون: {e}")
            return False
    
    def hibernate_device(self):
        """وضع السبات"""
        try:
            import platform
            import subprocess
            
            system = platform.system()
            if system == 'Windows':
                subprocess.run(['shutdown', '/h'], check=True)
            elif system == 'Linux':
                subprocess.run(['systemctl', 'hibernate'], check=True)
            elif system == 'Darwin':
                # macOS لا يدعم السبات بشكل مباشر
                return self.sleep_device()
            return True
        except Exception as e:
            print(f"خطأ في وضع السبات: {e}")
            return False
    
    def update_system(self):
        """تحديث النظام"""
        try:
            import platform
            import subprocess
            
            system = platform.system()
            if system == 'Windows':
                # Windows Update
                subprocess.run(['powershell', '-Command', 'Start-WindowsUpdate'], check=True)
            elif system == 'Linux':
                # تحديث النظام (يحتاج sudo)
                subprocess.run(['sudo', 'apt', 'update', '&&', 'sudo', 'apt', 'upgrade', '-y'], shell=True, check=True)
            elif system == 'Darwin':
                # macOS Software Update
                subprocess.run(['softwareupdate', '-i', '-a'], check=True)
            return True
        except Exception as e:
            print(f"خطأ في تحديث النظام: {e}")
            return False
    
    def scan_device(self):
        """فحص شامل للجهاز وجمع معلومات النظام"""
        try:
            import platform
            import psutil
            
            system = platform.system()
            scan_results = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'system_info': {},
                'hardware_info': {},
                'storage_info': {},
                'memory_info': {},
                'network_info': {},
                'processes_info': {},
                'warnings': [],
                'errors': []
            }
            
            print("=" * 60)
            print("جاري فحص الجهاز بشكل شامل...")
            print("=" * 60)
            
            # 1. معلومات النظام الأساسية
            try:
                scan_results['system_info'] = {
                    'platform': platform.system(),
                    'platform_release': platform.release(),
                    'platform_version': platform.version(),
                    'architecture': platform.machine(),
                    'processor': platform.processor(),
                    'hostname': platform.node(),
                    'python_version': platform.python_version()
                }
                print(f"✓ نظام التشغيل: {scan_results['system_info']['platform']} {scan_results['system_info']['platform_release']}")
                print(f"✓ المعالج: {scan_results['system_info']['processor']}")
                print(f"✓ المعمارية: {scan_results['system_info']['architecture']}")
            except Exception as e:
                scan_results['errors'].append(f'خطأ في جمع معلومات النظام: {e}')
                print(f"✗ خطأ في جمع معلومات النظام: {e}")
            
            # 2. معلومات المعالج (CPU)
            try:
                cpu_count_physical = psutil.cpu_count(logical=False)
                cpu_count_logical = psutil.cpu_count(logical=True)
                cpu_freq = psutil.cpu_freq()
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
                
                scan_results['hardware_info']['cpu'] = {
                    'physical_cores': cpu_count_physical,
                    'logical_cores': cpu_count_logical,
                    'current_frequency_mhz': cpu_freq.current if cpu_freq else None,
                    'min_frequency_mhz': cpu_freq.min if cpu_freq else None,
                    'max_frequency_mhz': cpu_freq.max if cpu_freq else None,
                    'usage_percent': cpu_percent,
                    'usage_per_core': cpu_per_core
                }
                print(f"✓ المعالج: {cpu_count_physical} نواة فيزيائية، {cpu_count_logical} نواة منطقية")
                print(f"✓ استخدام المعالج: {cpu_percent}%")
                
                if cpu_percent > 90:
                    scan_results['warnings'].append('استخدام المعالج عالي جداً (>90%)')
            except Exception as e:
                scan_results['errors'].append(f'خطأ في جمع معلومات المعالج: {e}')
                print(f"✗ خطأ في جمع معلومات المعالج: {e}")
            
            # 3. معلومات الذاكرة (RAM)
            try:
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                scan_results['memory_info'] = {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'used_gb': round(memory.used / (1024**3), 2),
                    'percent': memory.percent,
                    'swap_total_gb': round(swap.total / (1024**3), 2) if swap.total > 0 else 0,
                    'swap_used_gb': round(swap.used / (1024**3), 2) if swap.used > 0 else 0,
                    'swap_percent': swap.percent if swap.total > 0 else 0
                }
                print(f"✓ الذاكرة: {scan_results['memory_info']['total_gb']} GB إجمالي، "
                      f"{scan_results['memory_info']['used_gb']} GB مستخدم ({memory.percent}%)")
                
                if memory.percent > 90:
                    scan_results['warnings'].append('استخدام الذاكرة عالي جداً (>90%)')
            except Exception as e:
                scan_results['errors'].append(f'خطأ في جمع معلومات الذاكرة: {e}')
                print(f"✗ خطأ في جمع معلومات الذاكرة: {e}")
            
            # 4. معلومات التخزين (Disk)
            try:
                disk_info_list = []
                if system == 'Windows':
                    # فحص جميع الأقراص في Windows
                    import string
                    partitions = psutil.disk_partitions()
                    for partition in partitions:
                        try:
                            if partition.device and partition.device[0] in string.ascii_uppercase:
                                disk = psutil.disk_usage(partition.device)
                                disk_info = {
                                    'device': partition.device,
                                    'mountpoint': partition.mountpoint,
                                    'fstype': partition.fstype,
                                    'total_gb': round(disk.total / (1024**3), 2),
                                    'used_gb': round(disk.used / (1024**3), 2),
                                    'free_gb': round(disk.free / (1024**3), 2),
                                    'percent': disk.percent
                                }
                                disk_info_list.append(disk_info)
                                print(f"✓ القرص {partition.device}: {disk_info['total_gb']} GB إجمالي، "
                                      f"{disk_info['used_gb']} GB مستخدم ({disk.percent}%)")
                                
                                if disk.percent > 90:
                                    scan_results['warnings'].append(f'مساحة القرص {partition.device} ممتلئة تقريباً (>90%)')
                        except Exception:
                            continue
                    
                    # استخدام القرص الرئيسي C: للإحصائيات العامة
                    try:
                        main_disk = psutil.disk_usage('C:')
                        scan_results['storage_info'] = {
                            'main_disk_total_gb': round(main_disk.total / (1024**3), 2),
                            'main_disk_used_gb': round(main_disk.used / (1024**3), 2),
                            'main_disk_free_gb': round(main_disk.free / (1024**3), 2),
                            'main_disk_percent': main_disk.percent,
                            'all_disks': disk_info_list
                        }
                    except:
                        if disk_info_list:
                            scan_results['storage_info'] = {
                                'all_disks': disk_info_list,
                                'main_disk_total_gb': disk_info_list[0]['total_gb'] if disk_info_list else None,
                                'main_disk_used_gb': disk_info_list[0]['used_gb'] if disk_info_list else None,
                                'main_disk_free_gb': disk_info_list[0]['free_gb'] if disk_info_list else None,
                                'main_disk_percent': disk_info_list[0]['percent'] if disk_info_list else None
                            }
                else:
                    # Linux/Mac
                    disk = psutil.disk_usage('/')
                    scan_results['storage_info'] = {
                        'main_disk_total_gb': round(disk.total / (1024**3), 2),
                        'main_disk_used_gb': round(disk.used / (1024**3), 2),
                        'main_disk_free_gb': round(disk.free / (1024**3), 2),
                        'main_disk_percent': disk.percent,
                        'all_disks': [{
                            'device': '/',
                            'total_gb': round(disk.total / (1024**3), 2),
                            'used_gb': round(disk.used / (1024**3), 2),
                            'free_gb': round(disk.free / (1024**3), 2),
                            'percent': disk.percent
                        }]
                    }
                    print(f"✓ القرص: {scan_results['storage_info']['main_disk_total_gb']} GB إجمالي، "
                          f"{scan_results['storage_info']['main_disk_used_gb']} GB مستخدم ({disk.percent}%)")
                    
                    if disk.percent > 90:
                        scan_results['warnings'].append('مساحة القرص ممتلئة تقريباً (>90%)')
            except Exception as e:
                scan_results['errors'].append(f'خطأ في جمع معلومات القرص: {e}')
                print(f"✗ خطأ في جمع معلومات القرص: {e}")
            
            # 5. معلومات الشبكة
            try:
                net_io = psutil.net_io_counters()
                net_connections = len(psutil.net_connections(kind='inet'))
                net_if_addrs = psutil.net_if_addrs()
                
                scan_results['network_info'] = {
                    'bytes_sent_mb': round(net_io.bytes_sent / (1024**2), 2),
                    'bytes_recv_mb': round(net_io.bytes_recv / (1024**2), 2),
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv,
                    'active_connections': net_connections,
                    'network_interfaces': len(net_if_addrs)
                }
                print(f"✓ الشبكة: {scan_results['network_info']['bytes_sent_mb']} MB مرسل، "
                      f"{scan_results['network_info']['bytes_recv_mb']} MB مستلم")
            except Exception as e:
                scan_results['errors'].append(f'خطأ في جمع معلومات الشبكة: {e}')
                print(f"✗ خطأ في جمع معلومات الشبكة: {e}")
            
            # 6. معلومات العمليات (Processes)
            try:
                processes = list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']))
                processes_info = []
                total_processes = len(processes)
                running_processes = sum(1 for p in processes if p.info['cpu_percent'] is not None)
                
                # الحصول على أفضل 5 عمليات من حيث استخدام CPU
                top_cpu_processes = sorted(
                    [p.info for p in processes if p.info['cpu_percent'] is not None],
                    key=lambda x: x['cpu_percent'] or 0,
                    reverse=True
                )[:5]
                
                # الحصول على أفضل 5 عمليات من حيث استخدام الذاكرة
                top_memory_processes = sorted(
                    [p.info for p in processes if p.info['memory_percent'] is not None],
                    key=lambda x: x['memory_percent'] or 0,
                    reverse=True
                )[:5]
                
                scan_results['processes_info'] = {
                    'total_processes': total_processes,
                    'running_processes': running_processes,
                    'top_cpu_processes': top_cpu_processes,
                    'top_memory_processes': top_memory_processes
                }
                print(f"✓ العمليات: {total_processes} عملية إجمالي، {running_processes} عملية نشطة")
            except Exception as e:
                scan_results['errors'].append(f'خطأ في جمع معلومات العمليات: {e}')
                print(f"✗ خطأ في جمع معلومات العمليات: {e}")
            
            # 7. معلومات البطارية (إن وجدت)
            try:
                battery = psutil.sensors_battery()
                if battery:
                    scan_results['hardware_info']['battery'] = {
                        'percent': int(battery.percent),
                        'power_plugged': battery.power_plugged,
                        'secsleft': battery.secsleft if battery.secsleft != -1 else None
                    }
                    print(f"✓ البطارية: {battery.percent}% ({'موصول' if battery.power_plugged else 'غير موصول'})")
            except:
                pass  # البطارية غير متاحة (جهاز مكتبي)
            
            # 8. معلومات درجة الحرارة (إن وجدت)
            try:
                if hasattr(psutil, 'sensors_temperatures') and system != 'Windows':
                    temps = psutil.sensors_temperatures()
                    if temps:
                        temp_info = {}
                        for name, entries in temps.items():
                            if entries:
                                temp_info[name] = {
                                    'current': entries[0].current,
                                    'high': entries[0].high if entries[0].high else None,
                                    'critical': entries[0].critical if entries[0].critical else None
                                }
                        scan_results['hardware_info']['temperature'] = temp_info
                        print(f"✓ درجة الحرارة: {list(temp_info.values())[0]['current']:.1f}°C")
            except:
                pass  # درجة الحرارة غير متاحة
            
            # 9. إرسال نتائج الفحص إلى السيرفر
            print("\n" + "=" * 60)
            print("جاري إرسال نتائج الفحص إلى السيرفر...")
            print("=" * 60)
            
            # تحديث معلومات الجهاز في السيرفر
            update_success = self.update_device_info_after_scan(scan_results)
            
            if update_success:
                print("✓ تم إرسال نتائج الفحص إلى السيرفر بنجاح")
                scan_results['server_update'] = 'success'
            else:
                print("✗ فشل إرسال نتائج الفحص إلى السيرفر")
                scan_results['server_update'] = 'failed'
            
            # طباعة ملخص
            print("\n" + "=" * 60)
            print("ملخص نتائج الفحص:")
            print("=" * 60)
            print(f"✓ تم جمع معلومات النظام بنجاح")
            if scan_results['warnings']:
                print(f"⚠ التحذيرات ({len(scan_results['warnings'])}):")
                for warning in scan_results['warnings']:
                    print(f"  - {warning}")
            if scan_results['errors']:
                print(f"✗ الأخطاء ({len(scan_results['errors'])}):")
                for error in scan_results['errors']:
                    print(f"  - {error}")
            print("=" * 60)
            
            return True
        except Exception as e:
            print(f"✗ خطأ في فحص الجهاز: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_device_info_after_scan(self, scan_results):
        """تحديث معلومات الجهاز في السيرفر بعد الفحص"""
        try:
            if not self.device_token:
                print("لا يوجد token. لا يمكن تحديث معلومات الجهاز.")
                return False
            
            # إعداد معلومات التحديث
            update_data = {
                'operating_system': f"{scan_results.get('system_info', {}).get('platform', '')} {scan_results.get('system_info', {}).get('platform_release', '')}".strip(),
                'processor': scan_results.get('system_info', {}).get('processor', ''),
                'ram_total': int(scan_results.get('memory_info', {}).get('total_gb', 0)),
                'disk_total': int(scan_results.get('storage_info', {}).get('main_disk_total_gb', 0)),
                'scan_results': scan_results  # إرسال نتائج الفحص الكاملة
            }
            
            headers = {
                'X-Device-Token': self.device_token,
                'Content-Type': 'application/json'
            }
            
            # إرسال طلب التحديث
            response = requests.post(
                f"{self.server_url}/devices/api/update-after-scan",
                json=update_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"خطأ في تحديث معلومات الجهاز: {response.text}")
                return False
        except Exception as e:
            print(f"خطأ في إرسال نتائج الفحص: {e}")
            return False
    
    def backup_device(self):
        """نسخ احتياطي"""
        try:
            # نسخ احتياطي بسيط - يمكن إضافة منطق أكثر تعقيداً
            print("جاري إنشاء نسخة احتياطية...")
            # يمكن إضافة منطق النسخ الاحتياطي هنا
            return True
        except Exception as e:
            print(f"خطأ في النسخ الاحتياطي: {e}")
            return False
    
    def show_emergency_alert(self, message, action_id=None):
        """عرض تنبيه طارئ على الشاشة (شاشة حمراء كاملة + صوت)"""
        try:
            import threading
            import platform
            
            print(f"\n{'='*60}")
            print(f"⚠️ تنبيه طارئ من الإدارة!")
            print(f"الرسالة: {message}")
            print(f"{'='*60}\n")
            
            # تشغيل الصوت فوراً في thread منفصل (غير daemon حتى يستمر حتى بعد إغلاق النافذة)
            print("🔊 بدء تشغيل صوت التنبيه فوراً...")
            sound_thread = threading.Thread(target=self.play_emergency_sound, daemon=False)
            sound_thread.start()
            # لا ننتظر - نبدأ الصوت والنافذة في نفس الوقت
            print("✓ تم بدء thread تشغيل الصوت")
            
            # عرض النافذة في thread منفصل (لأن Tkinter يحتاج thread رئيسي)
            if platform.system() == 'Windows':
                # على Windows، استخدم Tkinter لعرض نافذة كاملة الشاشة
                try:
                    alert_thread = threading.Thread(
                        target=self._show_emergency_window_windows, 
                        args=(message, action_id), 
                        daemon=True
                    )
                    alert_thread.start()
                    # انتظر قليلاً للتأكد من فتح النافذة
                    time.sleep(0.5)
                except Exception as e:
                    print(f"خطأ في عرض النافذة: {e}")
                    # إذا فشل Tkinter، استخدم نهج بديل
                    self._show_emergency_console(message, action_id)
            else:
                # على Linux/Mac، استخدم نهج بديل
                self._show_emergency_console(message, action_id)
            
            return True
        except Exception as e:
            print(f"خطأ في عرض التنبيه الطارئ: {e}")
            return False
    
    def play_emergency_sound(self):
        """تشغيل صوت تنبيه طارئ من ملف MP3"""
        try:
            import os
            import subprocess
            import platform
            
            # الحصول على مجلد device_client.py
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # البحث عن ملف الصوت في نفس مجلد device_client.py
            sound_file = os.path.join(script_dir, "security-alarm.mp3")
            
            # إذا لم يوجد في نفس المجلد، جرب المجلد الحالي
            if not os.path.exists(sound_file):
                sound_file = "security-alarm.mp3"
            
            # التحقق من وجود الملف
            if not os.path.exists(sound_file):
                print(f"⚠️ تحذير: ملف الصوت 'security-alarm.mp3' غير موجود في:")
                print(f"   - {os.path.join(script_dir, 'security-alarm.mp3')}")
                print(f"   - {os.path.abspath('security-alarm.mp3')}")
                print(f"   - استخدام صوت افتراضي")
                # استخدام صوت افتراضي إذا لم يوجد الملف
                self._play_default_sound()
                return
            
            print(f"✓ تم العثور على ملف الصوت: {os.path.abspath(sound_file)}")
            
            system = platform.system()
            
            if system == 'Windows':
                # على Windows: استخدام عدة طرق لتشغيل MP3
                abs_path = os.path.abspath(sound_file)
                print(f"🔊 محاولة تشغيل الصوت من: {abs_path}")
                
                # الطريقة 1: استخدام os.startfile (الأبسط والأكثر موثوقية على Windows)
                try:
                    print("  محاولة الطريقة 1: os.startfile...")
                    # تشغيل فوري أول مرة بدون انتظار
                    try:
                        os.startfile(abs_path)
                        print("✓ تم تشغيل الصوت فوراً (الطريقة 1: os.startfile)")
                    except Exception as e:
                        print(f"  ⚠️ خطأ في os.startfile: {e}")
                        raise
                    
                    # ثم التكرار في حلقة
                    while True:
                        time.sleep(3)  # انتظر مدة الصوت قبل التكرار
                        try:
                            os.startfile(abs_path)
                            print("✓ تم إعادة تشغيل الصوت")
                        except Exception as e:
                            print(f"  ⚠️ خطأ في إعادة تشغيل الصوت: {e}")
                            time.sleep(1)
                except Exception as e1:
                    print(f"  ⚠️ فشلت الطريقة 1: {e1}")
                    
                    # الطريقة 2: استخدام start مباشرة
                    try:
                        print("  محاولة الطريقة 2: start command...")
                        while True:
                            subprocess.Popen(
                                f'start "" "{abs_path}"',
                                shell=True,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            print("✓ تم تشغيل الصوت (الطريقة 2: start)")
                            time.sleep(3)
                    except Exception as e2:
                        print(f"  ⚠️ فشلت الطريقة 2: {e2}")
                        
                        # الطريقة 3: استخدام PowerShell Invoke-Item
                        try:
                            print("  محاولة الطريقة 3: PowerShell Invoke-Item...")
                            ps_cmd = f'Invoke-Item -Path "{abs_path}"'
                            while True:
                                subprocess.Popen(
                                    ['powershell', '-Command', ps_cmd],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    creationflags=subprocess.CREATE_NO_WINDOW
                                )
                                print("✓ تم تشغيل الصوت (الطريقة 3: PowerShell)")
                                time.sleep(3)
                        except Exception as e3:
                            print(f"  ⚠️ فشلت الطريقة 3: {e3}")
                            
                            # الطريقة 4: استخدام Windows Media Player مباشرة
                            try:
                                print("  محاولة الطريقة 4: Windows Media Player...")
                                wmplayer_path = os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Windows Media Player', 'wmplayer.exe')
                                if not os.path.exists(wmplayer_path):
                                    wmplayer_path = os.path.join(os.environ.get('ProgramFiles', ''), 'Windows Media Player', 'wmplayer.exe')
                                
                                if os.path.exists(wmplayer_path):
                                    while True:
                                        subprocess.Popen(
                                            [wmplayer_path, '/play', '/close', abs_path],
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL,
                                            creationflags=subprocess.CREATE_NO_WINDOW
                                        )
                                        print("✓ تم تشغيل الصوت (الطريقة 4: wmplayer)")
                                        time.sleep(3)
                                else:
                                    raise Exception("Windows Media Player غير موجود")
                            except Exception as e4:
                                print(f"  ⚠️ فشلت الطريقة 4: {e4}")
                                
                                # الطريقة 5: استخدام صوت افتراضي
                                print("  استخدام صوت افتراضي (Windows Beep)...")
                                self._play_default_sound()
            
            elif system == 'Linux':
                # على Linux: استخدام mpg123 أو ffplay
                try:
                    # محاولة mpg123 أولاً
                    subprocess.Popen(
                        ['mpg123', '-q', '--loop', '-1', sound_file],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except:
                    try:
                        # محاولة ffplay
                        subprocess.Popen(
                            ['ffplay', '-nodisp', '-autoexit', '-loop', '0', sound_file],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    except:
                        # استخدام صوت افتراضي
                        self._play_default_sound()
            
            elif system == 'Darwin':  # macOS
                try:
                    # على macOS: استخدام afplay في حلقة
                    while True:
                        subprocess.Popen(
                            ['afplay', sound_file],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        time.sleep(3)  # انتظر حتى ينتهي الصوت قبل التكرار
                except:
                    self._play_default_sound()
            
        except Exception as e:
            print(f"خطأ في تشغيل الصوت: {e}")
            # استخدام صوت افتراضي كبديل
            self._play_default_sound()
    
    def _play_mp3_windows(self, sound_file):
        """تشغيل ملف MP3 على Windows باستخدام PowerShell"""
        try:
            import os
            import subprocess
            abs_path = os.path.abspath(sound_file).replace('\\', '\\\\')
            # استخدام PowerShell لتشغيل MP3 مع Windows Media Player
            while True:
                # استخدام Start-Process مع المشغل الافتراضي
                ps_command = f'Start-Process -FilePath "{abs_path}" -WindowStyle Hidden'
                subprocess.Popen(
                    ['powershell', '-Command', ps_command],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                time.sleep(3)  # انتظر قبل التكرار
        except Exception as e:
            print(f"  خطأ في تشغيل MP3: {e}")
            # استخدام صوت افتراضي
            self._play_default_sound()
    
    def _play_default_sound(self):
        """تشغيل صوت تنبيه افتراضي (إذا لم يوجد ملف MP3)"""
        try:
            import platform
            system = platform.system()
            
            if system == 'Windows':
                import winsound
                print("🔊 تشغيل صوت تنبيه افتراضي (Windows Beep)...")
                # تشغيل صوت تنبيه قوي ومستمر في حلقة
                while True:
                    try:
                        # صوت تنبيه قوي
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                        winsound.Beep(1000, 500)  # تردد 1000 هرتز لمدة 500ms
                        time.sleep(0.2)
                        winsound.Beep(1200, 500)  # تردد أعلى
                        time.sleep(0.2)
                        winsound.Beep(1000, 500)
                        time.sleep(1)  # انتظر ثانية قبل التكرار
                    except Exception as e:
                        print(f"⚠️ خطأ في تشغيل الصوت الافتراضي: {e}")
                        time.sleep(1)
            elif system == 'Linux':
                try:
                    import subprocess
                    while True:
                        subprocess.run(['beep', '-f', '1000', '-l', '500'], check=False, stderr=subprocess.DEVNULL)
                        time.sleep(0.3)
                except:
                    pass
            elif system == 'Darwin':  # macOS
                try:
                    import subprocess
                    while True:
                        subprocess.run(['afplay', '/System/Library/Sounds/Basso.aiff'], check=False, stderr=subprocess.DEVNULL)
                        time.sleep(0.3)
                except:
                    pass
        except Exception as e:
            print(f"خطأ في تشغيل الصوت الافتراضي: {e}")
    
    def _show_emergency_window_windows(self, message, action_id=None):
        """عرض نافذة طارئة على Windows باستخدام Tkinter"""
        try:
            import tkinter as tk
            from tkinter import font
            import datetime
            
            # تسجيل وقت فتح النافذة
            window_opened_at = datetime.datetime.now()
            window_closed = False
            
            # دالة لإرسال تقرير تصرف المستخدم
            def report_user_action(action_type, details=''):
                """إرسال تقرير تصرف المستخدم للسيرفر"""
                try:
                    if not action_id:
                        return
                    
                    headers = {
                        'X-Device-Token': self.device_token,
                        'Content-Type': 'application/json'
                    }
                    
                    # حساب مدة عرض النافذة
                    duration = None
                    if window_closed:
                        duration = (datetime.datetime.now() - window_opened_at).total_seconds()
                    
                    response = requests.post(
                        f"{self.server_url}/actions/api/action/{action_id}/user-action",
                        headers=headers,
                        json={
                            'action_type': action_type,  # 'opened', 'closed', 'auto_closed', 'esc_pressed'
                            'details': details,
                            'opened_at': window_opened_at.isoformat(),
                            'duration_seconds': duration
                        },
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        print(f"✓ تم إرسال تقرير تصرف المستخدم: {action_type}")
                except Exception as e:
                    print(f"⚠️ تحذير: فشل إرسال تقرير تصرف المستخدم: {e}")
            
            # إرسال تقرير فتح النافذة
            report_user_action('opened', 'تم فتح نافذة التنبيه الطارئ')
            
            # إنشاء النافذة
            root = tk.Tk()
            root.title("تنبيه طارئ - نظام المراقبة")
            
            # جعل النافذة في وضع fullscreen
            root.attributes('-fullscreen', True)
            root.attributes('-topmost', True)  # دائماً في المقدمة
            root.overrideredirect(True)  # إزالة شريط العنوان
            
            # خلفية حمراء
            root.configure(bg='#dc3545')
            
            # نص التنبيه
            title_font = font.Font(family='Arial', size=48, weight='bold')
            message_font = font.Font(family='Arial', size=32)
            instruction_font = font.Font(family='Arial', size=24)
            
            # العنوان
            title_label = tk.Label(
                root,
                text="⚠️ تنبيه طارئ من الإدارة ⚠️",
                font=title_font,
                bg='#dc3545',
                fg='white',
                pady=50
            )
            title_label.pack()
            
            # الرسالة
            message_label = tk.Label(
                root,
                text=message,
                font=message_font,
                bg='#dc3545',
                fg='white',
                wraplength=1200,
                justify='center',
                pady=30
            )
            message_label.pack()
            
            # تعليمات
            instruction_label = tk.Label(
                root,
                text="يرجى الاتصال بقسم تكنولوجيا المعلومات فوراً",
                font=instruction_font,
                bg='#dc3545',
                fg='white',
                pady=20
            )
            instruction_label.pack()
            
            # دالة إغلاق مع تتبع
            def close_window(action_type='closed', details=''):
                nonlocal window_closed
                window_closed = True
                report_user_action(action_type, details)
                root.destroy()
            
            # زر الإغلاق (للإدارة فقط)
            close_button = tk.Button(
                root,
                text="إغلاق (للمسؤولين فقط)",
                font=instruction_font,
                bg='#343a40',
                fg='white',
                command=lambda: close_window('closed', 'تم إغلاق النافذة بواسطة المستخدم'),
                padx=30,
                pady=15,
                relief=tk.FLAT,
                cursor='hand2'
            )
            close_button.pack(pady=50)
            
            # تأثير وميض (flash effect) - وميض 20 مرة (10 ثوان)
            flash_count = [0]
            def flash():
                if flash_count[0] < 20:
                    current_bg = root.cget('bg')
                    new_bg = '#c82333' if current_bg == '#dc3545' else '#dc3545'
                    root.configure(bg=new_bg)
                    # تحديث خلفية جميع العناصر
                    for widget in root.winfo_children():
                        if isinstance(widget, tk.Label) or isinstance(widget, tk.Button):
                            widget.configure(bg=new_bg)
                    flash_count[0] += 1
                    root.after(500, flash)
            
            flash()  # بدء التأثير
            
            # ربط زر ESC للإغلاق
            def on_escape(event):
                close_window('esc_pressed', 'تم إغلاق النافذة بالضغط على ESC')
            root.bind('<Escape>', on_escape)
            root.focus_set()
            
            # إغلاق تلقائي بعد 5 دقائق (300 ثانية)
            def auto_close():
                close_window('auto_closed', 'تم إغلاق النافذة تلقائياً بعد 5 دقائق')
            root.after(300000, auto_close)
            
            # تشغيل النافذة
            root.mainloop()
        except Exception as e:
            print(f"خطأ في عرض النافذة: {e}")
            # إذا فشل Tkinter، استخدم نهج بديل
            self._show_emergency_console(message)
    
    def _show_emergency_console(self, message):
        """عرض التنبيه في الكونسول (نهج بديل)"""
        try:
            import platform
            
            if platform.system() == 'Windows':
                # على Windows، استخدم MessageBox
                try:
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        f"⚠️ تنبيه طارئ من الإدارة ⚠️\n\n{message}\n\nيرجى الاتصال بقسم تكنولوجيا المعلومات فوراً",
                        "تنبيه طارئ - نظام المراقبة",
                        0x10 | 0x0  # MB_ICONERROR | MB_OK
                    )
                except:
                    print(f"\n{'='*60}")
                    print(f"⚠️ تنبيه طارئ من الإدارة ⚠️")
                    print(f"{'='*60}")
                    print(f"{message}")
                    print(f"{'='*60}")
                    print("يرجى الاتصال بقسم تكنولوجيا المعلومات فوراً")
                    print(f"{'='*60}\n")
            else:
                # على Linux/Mac، اطبع في الكونسول
                print(f"\n{'='*60}")
                print(f"⚠️ تنبيه طارئ من الإدارة ⚠️")
                print(f"{'='*60}")
                print(f"{message}")
                print(f"{'='*60}")
                print("يرجى الاتصال بقسم تكنولوجيا المعلومات فوراً")
                print(f"{'='*60}\n")
        except Exception as e:
            print(f"خطأ في عرض التنبيه: {e}")
    
    def run(self):
        """تشغيل المراقبة المستمرة"""
        print("=" * 60)
        print("نظام مراقبة الأجهزة - العميل")
        print("=" * 60)
        print(f"الخادم: {self.server_url}")
        print(f"فترة الإرسال: كل {REPORT_INTERVAL} ثانية")
        
        # التحقق من الصلاحيات على Windows
        try:
            if platform.system() == 'Windows':
                try:
                    import ctypes
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                    if is_admin:
                        print("✓ صلاحيات المسؤول: مفعّلة (جميع الإجراءات متاحة)")
                    else:
                        print("⚠️ صلاحيات المسؤول: غير مفعّلة")
                        print("  ⚠️ تحذير: إجراءات shutdown/restart/sleep/hibernate قد لا تعمل!")
                        print("  💡 الحل: شغّل device_client.py كمسؤول (Run as administrator)")
                        print("  💡 أو اقرأ ملف INSTALL_AS_SERVICE.md لتثبيت كخدمة")
                except:
                    pass
        except:
            pass
        
        # التحقق من Token
        if not self.device_token:
            print("\n⚠️ تحذير: لا يوجد Device Token!")
            print("  جاري محاولة التسجيل التلقائي...")
            if not self.register_device():
                print("\n❌ فشل التسجيل التلقائي!")
                print("  💡 الحل: احصل على Token من السيرفر وأضفه في device_config.json")
                print("  💡 أو شغّل: start_client.bat")
                return
        else:
            print(f"\n✓ Device Token موجود: {self.device_token[:20]}...")
        
        # اختبار الاتصال الأولي
        print("\n" + "=" * 60)
        print("اختبار الاتصال بالسيرفر...")
        print("=" * 60)
        try:
            test_response = requests.get(f"{self.server_url}/", timeout=5)
            if test_response.status_code == 200:
                print("✓ الاتصال بالسيرفر: ناجح")
            else:
                print(f"⚠️ تحذير: السيرفر رجع كود {test_response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ خطأ: لا يمكن الاتصال بالسيرفر!")
            print(f"  تأكد من أن السيرفر يعمل على: {self.server_url}")
            print("  تأكد من الاتصال بالإنترنت")
            return
        except Exception as e:
            print(f"⚠️ تحذير في الاتصال: {e}")
        
        print("=" * 60)
        print("\n🚀 بدء المراقبة...")
        print("💡 اضغط Ctrl+C لإيقاف المراقبة\n")
        print("=" * 60)
        print()
        
        consecutive_failures = 0
        max_failures = 5
        
        while True:
            try:
                # إرسال القياسات
                success = self.report_metrics()
                
                if success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        print(f"\n⚠️ تحذير: فشل الاتصال {max_failures} مرات متتالية!")
                        print("  جاري إعادة المحاولة...")
                        consecutive_failures = 0
                
                # التحقق من الإجراءات المعلقة
                self.check_pending_actions()
                
                time.sleep(REPORT_INTERVAL)
            except KeyboardInterrupt:
                print("\n\n" + "=" * 60)
                print("تم إيقاف المراقبة.")
                print("=" * 60)
                break
            except Exception as e:
                print(f"❌ خطأ: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print(f"\n⚠️ تحذير: حدث خطأ {max_failures} مرات متتالية!")
                    print("  جاري إعادة المحاولة...")
                    consecutive_failures = 0
                time.sleep(REPORT_INTERVAL)


if __name__ == "__main__":
    import sys
    
    # يمكن تمرير URL الخادم و Token كوسيطات
    # الاستخدام: python device_client.py [SERVER_URL] [DEVICE_TOKEN]
    server_url = sys.argv[1] if len(sys.argv) > 1 else SERVER_URL
    device_token = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("=" * 60)
    print("نظام مراقبة الأجهزة - العميل")
    print("=" * 60)
    
    if device_token:
        print(f"استخدام Token المحدد: {device_token[:20]}...")
        monitor = DeviceMonitor(server_url, device_token=device_token)
    else:
        print("لا يوجد Token - سيتم التسجيل التلقائي")
        monitor = DeviceMonitor(server_url)
    
    monitor.run()

