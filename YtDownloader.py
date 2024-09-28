import wx
import wx.adv
import yt_dlp
import requests
from PIL import Image
from io import BytesIO
import os
import threading
import traceback
# import faulthandler
# faulthandler.enable()




class CustomListCtrl(wx.ListCtrl):
    def __init__(self, parent, *args, **kw):
        super(CustomListCtrl, self).__init__(parent, *args, **kw)

        # Bind paint event for custom drawing
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnPaint(self, event):
        event.Skip()  # Allow the default painting first

        # Custom paint logic (if you want to do more drawing, e.g., borders)
        dc = wx.PaintDC(self)
        width, height = self.GetSize()

        # Draw custom borders (if needed)
        row_height = self.GetItemRect(0).height if self.GetItemCount() > 0 else 25
        num_items = self.GetItemCount()

        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0), 1))
        for i in range(num_items):
            rect = self.GetItemRect(i)
            y = rect.y + rect.height
            dc.DrawLine(0, y, width, y)
        self.Update()



class YTDownloader(wx.Frame):
    def __init__(self, *args, **kwargs):
        super(YTDownloader, self).__init__(*args, **kwargs)
        self.SetSize((750, 450))
        self.SetBackgroundColour('#2c001e') 
        
        self.InitUI()
        
    def InitUI(self):
        panel = wx.Panel(self)
        self.panel = panel

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)

        # URL input
        url_label = wx.StaticText(panel, label='YouTube URL:')
        url_label.SetBackgroundColour('#f9f7f6') 
        hbox1.Add(url_label, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.url_input = wx.TextCtrl(panel, size=(300,20))
        hbox1.Add(self.url_input, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        get_file_details = wx.Button(panel, label='Get_url_info')
        get_file_details.Bind(wx.EVT_BUTTON, self.Get_url_info)
        hbox1.Add(get_file_details, 0, wx.ALIGN_CENTER | wx.ALL, 5)


        exit_btn = wx.Button(panel, label='Exit')
        exit_btn.Bind(wx.EVT_BUTTON, self.OnExit)
        hbox1.Add(exit_btn, 0, wx.ALIGN_CENTER | wx.ALL, 5) 

        script_path = os.path.abspath(__file__)
        script_directory = os.path.dirname(script_path)
        loader_path = os.path.join(script_directory, "loader.gif")
        gif = wx.adv.Animation(loader_path)
        self.anim_ctrl = wx.adv.AnimationCtrl(panel, -1, gif)
        hbox2.Add(self.anim_ctrl, 0, wx.ALIGN_CENTER | wx.ALL, 5) 


        # Radio buttons for selecting audio or video
        self.radio_audio = wx.RadioButton(panel, label='Audio Only', style=wx.RB_GROUP)
        self.radio_audio.SetBackgroundColour('#f9f7f6') 
        self.radio_video = wx.RadioButton(panel, label='Video')
        self.radio_video.SetBackgroundColour('#f9f7f6') 

        hbox2.Add(self.radio_audio, 0, wx.ALIGN_CENTER | wx.ALL, 5) 

        hbox2.Add(self.radio_video, 0, wx.ALIGN_CENTER | wx.ALL, 5) 

        

        # ListCtrl for displaying download options
        # self.options_list = wx.ListCtrl(panel, style=wx.LC_REPORT)
        self.options_list = CustomListCtrl(panel, style=wx.LC_REPORT)
        self.options_list.InsertColumn(0, 'Thumbnail', width=100)
        self.options_list.InsertColumn(1, 'Format', width=100)
        self.options_list.InsertColumn(2, 'Resolution', width=100)
        self.options_list.InsertColumn(3, 'File_ext', width=100)
        self.options_list.InsertColumn(4, 'Filesize(MB)', width=100)
        self.options_list.InsertColumn(5, 'Download', width=100)
        self.options_list.InsertColumn(6, 'Downloading progress %', width=100)


        self.index_of_percentage_of_download_file = 6
        # self.options_list.InsertColumn(5, 'Browse', width=100)

        hbox3.Add(self.options_list, 1, wx.EXPAND | wx.ALL, 5) 


        vbox.Add(hbox1, 0, wx.EXPAND | wx.ALL, 5)    

        vbox.Add(hbox2, 0, wx.EXPAND | wx.ALL, 5)    

        vbox.Add(hbox3, 1, wx.EXPAND | wx.ALL, 5)    

        # Initialize the image list for thumbnails
        self.image_list = wx.ImageList(100, 100)
        self.options_list.SetImageList(self.image_list, wx.IMAGE_LIST_SMALL)

        self.file_name = None
        self.video_flag = None
        self.sleep_obj = threading.Event()

        # Bind events
        self.radio_audio.Bind(wx.EVT_RADIOBUTTON, self.OnRadioSelect)
        self.radio_video.Bind(wx.EVT_RADIOBUTTON, self.OnRadioSelect)
        
        # self.options_list.Bind(wx.EVT_LISTBOX_DCLICK, self.OnDownload)
        # self.options_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnDownload)
        self.options_list.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        # self.options_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_left_down)
        self.options_list.Bind(wx.EVT_LIST_COL_BEGIN_DRAG, self.on_column_resize)


        panel.SetSizer(vbox)
        self.audio_files = []
        self.video_files = []
        self.thumbnail_url = None

        self.lock = threading.Lock()
        
        self.SetTitle('YouTube Downloader')
        self.Centre()

    def on_column_resize(self, event):
        try:
            col_index = event.GetColumn()
            # Reset the width of the column to the original width
            if col_index>-1:  # Fix the 5th column (Progress)
                for i in range(self.options_list.ColumnCount):
                    self.options_list.SetColumnWidth(i, 100)  # Fix the width to 100px
            else:
                event.Skip()
        except Exception as e:
            print("error ---",str(e))

    def Get_url_info(self, event):
        try:
            url = self.url_input.GetValue()
            
            if not url:
                url = "https://youtube.com/watch?v=UlWAjd9bcKw"
                self.url_input.SetLabel(url)

            
            th_f = threading.Thread(target=self.FindAllOptionsForAudioVideo)
            th_f.start()
        except Exception as e:
            # Capture the full traceback
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            
            # Optionally, print the error to the console for more detailed debugging
            print(error_message)
            wx.MessageBox(f'Error: {str(e)}', 'Get_url_info', wx.OK | wx.ICON_ERROR)
            
    def FindAllOptionsForAudioVideo(self):
        try:
            url = self.url_input.GetValue()
            if not url:
                wx.MessageBox('Please enter a valid URL.', 'FindAllOptionsForAudioVideo', wx.OK | wx.ICON_ERROR)
                return
            if not self.lock.locked():
                wx.CallAfter(self.anim_ctrl.Play)
                self.lock.acquire()
                # Clear previous options
                self.options_list.DeleteAllItems()
                self.image_list.RemoveAll()

                # Fetch video and audio formats
                ydl_opts = {'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=False)
                    formats = info_dict.get('formats', [])
                    self.file_name = info_dict.get('title')
                self.thumbnail_url = info_dict.get('thumbnail', '')

                for fmt in formats:
                    format_id = fmt.get('format_id', None)
                    format_note = fmt.get('format_note', None)
                    resolution = fmt.get('resolution', None)
                    filesize = fmt.get('filesize', None)
                    file_url = fmt.get('url',None)
                    file_ext = fmt.get('ext',None)


                    # Filter based on extensions
                    if filesize and file_url and resolution and format_id and format_note and file_ext != "webm":
                        if fmt.get('video_ext') != 'none':
                            self.video_files.append((format_id,resolution,file_ext,str(filesize//(1024*1024)),"Download"))
                        elif fmt.get('audio_ext') != 'none':
                            self.audio_files.append((format_id,resolution,file_ext,str(filesize//(1024*1024)),"Download"))
                        # Sort the video_files list based on the filesize (index 3)
                        self.video_files.sort(key=lambda x: int(x[3]))  # Sort in ascending order
                        self.audio_files.sort(key=lambda x: int(x[3]))

                        # If you want to sort in descending order, you can use:
                        # self.video_files.sort(key=lambda x: int(x[3]), reverse=True)

                        
                self.lock.release()
                self.radio_video.SetValue(True)
                self.radio_audio.SetValue(False)
                wx.CallAfter(self.PopulateOptions,False)
                self.options_list.Update()
                wx.CallAfter(self.anim_ctrl.Stop)
            else:
                print("another thread is already using lock")
            # self.panel.Update()

            # wx.MessageBox('File info is collected!', 'Success', wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            # Capture the full traceback
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            
            # Optionally, print the error to the console for more detailed debugging
            print(error_message)
            wx.MessageBox(f'Error: {str(e)}', 'FindAllOptionsForAudioVideo', wx.OK | wx.ICON_ERROR)
        finally:
            pass
            
    def download_file(self, url, ydl_opts,index):
        # Open directory dialog for the user to choose download location
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            wx.MessageBox('Download completed!', 'Success', wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            # Capture the full traceback
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            
            # Optionally, print the error to the console for more detailed debugging
            print(error_message)
            wx.MessageBox(f'Error: {str(e)}', 'download_file', wx.OK | wx.ICON_ERROR)
        finally:
            wx.CallAfter(self.anim_ctrl.Stop)
    
    def on_left_down(self, event):
        try:
            x, y = event.GetPosition()
            item, flags = self.options_list.HitTest((x, y))

            if item != wx.NOT_FOUND:
                # Get the full rectangle of the clicked row
                rect = self.options_list.GetItemRect(item)

                # Manually calculate the position of the third column (Download button)
                col2_x_start = self.options_list.GetColumnWidth(0) + self.options_list.GetColumnWidth(1) +self.options_list.GetColumnWidth(2) + self.options_list.GetColumnWidth(3) + self.options_list.GetColumnWidth(4)
                col2_x_end = col2_x_start + self.options_list.GetColumnWidth(6)

                if col2_x_start <= x <= col2_x_end:
                    # wx.MessageBox(f"Download clicked for Option {item + 1}")
                    wx.CallAfter(self.OnDownload,item)
        except Exception as e:
            event.Skip()
            pass

    def OnDownload(self, index):
        try:
            format_id = self.options_list.GetItemText(index, 1)  # Assuming the format code is in the second column
            wx.CallAfter(self.anim_ctrl.Play)
            url = self.url_input.GetValue()
            if not url:
                wx.MessageBox('Please enter a valid URL.', 'Error', wx.OK | wx.ICON_ERROR)
                return
            if self.video_flag:
                format_id = format_id+"+140"
            ydl_opts = {
                'format': format_id,
                'outtmpl': self.file_name+'.%(ext)s',
            }
            with wx.DirDialog(None, "Choose download location", style=wx.DD_DEFAULT_STYLE) as dir_dialog:
                if dir_dialog.ShowModal() == wx.ID_OK:
                    download_path = dir_dialog.GetPath()

                    # Update ydl_opts with the chosen download path
                    ydl_opts['outtmpl'] = f"{download_path}/%(title)s.%(ext)s"
                    dt = threading.Thread(target=self.start_download,args=(url, ydl_opts, index))
                    dt.start()
                else:
                    print("Not choosed any directory")
                    wx.CallAfter(self.anim_ctrl.Stop)
            
        except Exception as e:
            # Capture the full traceback
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            
            # Optionally, print the error to the console for more detailed debugging
            print(error_message)
            print("error", str(e))
            wx.MessageBox(f'Error: {str(e)}', 'OnDownload', wx.OK | wx.ICON_ERROR)
    
    def start_download(self, url, ydl_opts, index):
        # Define a hook function to capture the download progress
        def progress_hook(d):
            if d['status'] == 'downloading':
                # percentage = d['_percent_str'].strip()
                percentage = str((d['downloaded_bytes']*100)/d['total_bytes'])
                wx.CallAfter(self.update_progress, index, percentage)

        # Add the progress_hook to the download options
        ydl_opts['progress_hooks'] = [progress_hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            # wx.CallAfter(wx.MessageBox, 'Download completed!', 'Success', wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.CallAfter(wx.MessageBox, f"Download failed: {str(e)}", 'Error', wx.OK | wx.ICON_ERROR)
        finally:
            wx.CallAfter(self.anim_ctrl.Stop)

    def update_progress(self, index, percentage):
        # Update the percentage in the 6th column (column index 5)
        self.options_list.SetItem(index, self.index_of_percentage_of_download_file, percentage)
        
    def OnRadioSelect(self, event):
        # Enable or disable the resolution choice based on the radio selection
        try:
            url = self.url_input.GetValue()
            if not url:
                
                wx.MessageBox('Please enter a valid URL.', 'Error', wx.OK | wx.ICON_ERROR)
                return
            wx.CallAfter(self.anim_ctrl.Play)
            
            if self.radio_audio.GetValue():
                self.radio_video.SetValue(False)
                self.radio_audio.SetValue(True)
                wx.CallAfter(self.PopulateOptions,audio_only=True)
                # thrd = threading.Thread(target=self.PopulateOptions,args=(True,))
                # thrd.setDaemon = True
                # thrd.start()
            else:
                # th_rd = threading.Thread(target=self.PopulateOptions,args=(False,))
                # th_rd.setDaemon = True
                # th_rd.start()
                self.radio_video.SetValue(True)
                self.radio_audio.SetValue(False)
                wx.CallAfter(self.PopulateOptions,audio_only=False)
        except Exception as e:
            # Capture the full traceback
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            
            # Optionally, print the error to the console for more detailed debugging
            print(error_message)
            wx.MessageBox(f'Error: {str(e)}', 'OnRadioSelect', wx.OK | wx.ICON_ERROR)
                      
    def PopulateOptions(self, audio_only):
        try:

            if audio_only:
                self.video_flag = False
            else:
                self.video_flag = True
            url = self.url_input.GetValue()
            if not url:
                wx.MessageBox('Please enter a valid URL.', 'Error', wx.OK | wx.ICON_ERROR)
                return
            self.sleep_obj.wait(1)
            with self.lock:
            
                # Clear previous options
                self.options_list.DeleteAllItems()
                self.image_list.RemoveAll()
                wx.Yield()
                wx.CallAfter(self.panel.Layout)
                wx.CallAfter(self.panel.Refresh)
                if self.thumbnail_url:
                    thumbnail_path = self.download_thumbnail(self.thumbnail_url)
                    img = wx.Image(thumbnail_path, wx.BITMAP_TYPE_ANY)
                    img = img.Scale(150, 100, wx.IMAGE_QUALITY_HIGH)  
                    thumbnail = img.ConvertToBitmap()
                else:
                    thumbnail = wx.Image("default_thumbnail.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
                data_for_populate = None
                if audio_only:
                    data_for_populate = self.audio_files
                else:
                    data_for_populate = self.video_files

                
                for fmt in data_for_populate:
                    # print("fmt---",fmt)
                    format_id = fmt[0]
                    resolution = fmt[1]
                    file_ext = fmt[2]
                    filesize = fmt[3]
                    download = fmt[4]

                    if self.image_list:
                        thumbnail_idx = self.image_list.Add(thumbnail)
                        index = self.options_list.InsertItem(self.options_list.GetItemCount(), '', thumbnail_idx)
                        wx.CallAfter(self.options_list.SetItem, index, 1, format_id)
                        wx.CallAfter(self.options_list.SetItem, index, 2, resolution)
                        wx.CallAfter(self.options_list.SetItem, index, 3, file_ext)
                        wx.CallAfter(self.options_list.SetItem, index, 4, filesize)
                        wx.CallAfter(self.options_list.SetItem, index, 5, download)
                        # self.options_list.SetItem(index, 1, format_id)
                        # self.options_list.SetItem(index, 2, resolution)
                        # self.options_list.SetItem(index, 3, filesize)

    
                
            # wx.CallAfter(self.panel.Layout)
            # wx.CallAfter(self.panel.Refresh)

        except Exception as e:
            # Capture the full traceback
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            
            # Optionally, print the error to the console for more detailed debugging
            print(error_message)
            wx.MessageBox(f'Error: {str(e)}', 'PopulateOptions', wx.OK | wx.ICON_ERROR)
        finally:
            wx.CallAfter(self.anim_ctrl.Stop)
    
    def on_paint(self, event):
        pass
        # event.Skip()  # Allow the default paint first
        # dc = wx.ClientDC(self.options_list)
        # width, height = self.options_list.GetSize()

        # # Draw row borders
        # row_height = 25  # Adjust this as needed
        # for i in range(10):  # Loop through rows
        #     y = i * row_height
        #     dc.SetPen(wx.Pen(wx.Colour(0, 0, 0), 1))  # Set black border color
        #     dc.DrawLine(0, y, width, y)
            
    def download_thumbnail(self, url):
        """
        Download the thumbnail from the given URL and save it locally.

        :param url: URL of the thumbnail image.
        :param format_id: Unique identifier for the format (used to name the file).
        :return: Path to the saved thumbnail image.
        """
        try:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            thumbnail_path = "thumbnail.png"
            img.save(thumbnail_path)
            return thumbnail_path
        except Exception as e:
            # Capture the full traceback
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            
            # Optionally, print the error to the console for more detailed debugging
            print(error_message)
            print(f"Error downloading thumbnail: {str(e)}")
            wx.MessageBox(f'Error: {str(e)}', 'download_thumbnail', wx.OK | wx.ICON_ERROR)
            return "default_thumbnail.png"  # Return a default image in case of error

    def OnExit(self, event):
        self.Close()





def main():
    app = wx.App(False)
    frame = YTDownloader(None)
    frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()