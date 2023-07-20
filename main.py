import glob
import io
import os
import time
from dataclasses import dataclass

import cv2
import flet as ft
import numpy as np
import platformdirs
from PIL import Image, ImageOps
from cairosvg import svg2png


@dataclass
class Paths:
    input: str
    output: str


def main(page: ft.Page):
    cache_dir = platformdirs.user_cache_dir('CoatOfArmsFitter', 'slashfast')
    cache_path = f'{cache_dir}/paths.cache'

    selected_paths = Paths('', '')
    page.window_width = 548
    page.window_height = 374
    page.window_resizable = False
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.update()

    def pick_files_result(e: ft.FilePickerResultEvent):
        if e.path:
            if e.control.data == 'input':
                selected_paths.input = e.path
                input_path_field.value = e.path
            if e.control.data == 'output':
                selected_paths.output = e.path
                output_path_field.value = e.path
            if selected_paths.input and selected_paths.output:
                start_button.disabled = False
        page.update()

    def clean_error(e):
        e.control.error_text = None
        e.control.update()

    def start(_):
        input_folder = selected_paths.input
        output_folder = selected_paths.output

        extensions = ['*.png', '*.jpg', '*.gif', '*.webp', '*.svg']
        files = [f for e in extensions for f in glob.glob(f'{input_folder}/{e}')]
        progress_bar.visible = True
        progress_bar_current.visible = True
        progress_bar.update()
        target_radius = 95
        size = 200
        diameter = 190
        amount = len(files)
        for c, f in enumerate(files):
            output_name = os.path.basename(f)
            output = f'{output_folder}/{os.path.splitext(output_name)[0]}.png'
            if os.path.splitext(os.path.basename(f))[1] == '.svg':
                with io.BytesIO() as buffer:
                    svg2png(url=f, dpi=72, write_to=buffer)
                    image = Image.open(buffer).copy()
                    buffer.close()
            else:
                image = Image.open(f).convert('RGBA')
                image = image.crop(image.getbbox())
            image = ImageOps.contain(image, (diameter, diameter), 5)
            mask = Image.new('L', image.size, 0)
            mask.paste(255, (0, 0), image.split()[3])
            mask = np.asarray(mask)  # noqa
            scale_percent = 60.0
            radius = 0
            mask = np.asarray(mask)
            while target_radius != radius:
                width = round(mask.shape[1] * scale_percent / 100)
                height = round(mask.shape[0] * scale_percent / 100)
                resized = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
                contours, _ = cv2.findContours(resized, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_L1)
                cnt = contours[0]
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                radius = round(radius)
                if radius < target_radius:
                    scale_percent += 0.1
                    continue
                elif radius > target_radius:
                    scale_percent -= 0.1
                    continue
                elif radius == target_radius:
                    center = (round(x), round(y))
                    image = image.resize((width, height), 5)
                    background = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                    # draw = ImageDraw.Draw(background)
                    background.paste(image, ((size - (center[0] * 2)) // 2, (size - (center[1] * 2)) // 2))
                    # draw.ellipse((5, 5) + (194, 194), fill=None, outline=(0, 255, 0, 255), width=1)
                    background.save(output)
            progress_bar_current.value = output_name
            progress_bar.value = (c + 1) * (1.0 / amount)
            progress_bar_percents.value = f'{round(progress_bar.value * 100)}%'
            page.update()
        time.sleep(0.5)
        progress_bar_current.visible = False
        page.snack_bar = ft.SnackBar(
            content=ft.Text('Операция завершена'),
        )
        page.snack_bar.open = True
        page.update()

    def open_dlg_modal(_):
        page.dialog = dlg_modal
        dlg_modal.open = True
        ft.View()
        page.update()

    def close_dlg(_):
        dlg_modal.open = False
        input_path_field.error_text = None
        output_path_field.error_text = None
        page.update()

    def accept_dlg(_):
        input_path_valid = os.path.exists(input_path_field.value)
        output_path_valid = os.path.exists(output_path_field.value)
        summary = input_path_valid and output_path_valid
        if not input_path_valid:
            input_path_field.error_text = 'Укажите корректный путь'
            input_path_field.update()
        if not output_path_valid:
            output_path_field.error_text = 'Укажите корректный путь'
            output_path_field.update()
        if summary:
            if not os.path.exists(cache_path):
                os.mkdir(cache_dir)
            with open(cache_path, 'wb') as cache:
                cache.truncate()
                cache.write(input_path_field.value.encode('utf-8') + b'\n')
                cache.write(output_path_field.value.encode('utf-8') + b'\n')
            dlg_modal.open = False
        page.update()

    input_dialog = ft.FilePicker(on_result=pick_files_result, data='input')
    output_dialog = ft.FilePicker(on_result=pick_files_result, data='output')
    open_files_button = ft.ElevatedButton('Открыть файлы', icon=ft.icons.UPLOAD_FILE, on_click=open_dlg_modal)
    start_button = ft.ElevatedButton('Начать', icon=ft.icons.UPLOAD_FILE, on_click=start, disabled=True)
    progress_bar = ft.ProgressBar(width=380, value=0.0, visible=False)
    progress_bar_current = ft.Text()
    progress_bar_percents = ft.Text()
    input_path_field = ft.TextField(
        label='Путь для чтения',
        width=float('inf'),
        height=48,
        text_size=12,
        suffix=ft.IconButton(
            icon=ft.icons.FOLDER,
            on_click=lambda _: input_dialog.get_directory_path(dialog_title='Путь для чтения'),
        ),
        on_change=clean_error
    )
    output_path_field = ft.TextField(
        label='Путь для записи',
        width=float('inf'),
        height=48,
        text_size=12,
        suffix=ft.IconButton(
            icon=ft.icons.FOLDER,
            on_click=lambda _: output_dialog.get_directory_path(dialog_title='Путь для записи')
        ),
        on_change=clean_error
    )
    dlg_modal = ft.AlertDialog(
        title=ft.Text('Выберите папки', size=20),
        content=ft.Column(
            [
                ft.Container(input_path_field, height=64, width=400),
                ft.Container(output_path_field, height=64, width=400)
            ],
            tight=True,
            alignment=ft.alignment.center
        ),
        actions=[
            ft.TextButton('Отмена', on_click=close_dlg),
            ft.TextButton('Принять', on_click=accept_dlg),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(input_dialog)
    page.overlay.append(output_dialog)
    page.add(
        ft.Container(
            ft.Row(
                [
                    open_files_button,
                    start_button
                ],
                alignment=ft.MainAxisAlignment.CENTER,

            ),
            padding=ft.padding.only(bottom=20)
        ),
        ft.Column(
            [
                ft.Container(
                    progress_bar_current,
                    alignment=ft.alignment.center),
                progress_bar,
                ft.Container(
                    progress_bar_percents,
                    alignment=ft.alignment.center),
            ],
            width=380,
            height=40,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
    )

    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as file:
            input_path = file.readline().decode('utf-8').rstrip()
            output_path = file.readline().decode('utf-8').rstrip()
        input_path_field.value = input_path
        output_path_field.value = output_path
        selected_paths.input = input_path
        selected_paths.output = output_path
        start_button.disabled = False
        page.snack_bar = ft.SnackBar(
            content=ft.Text('Выбраны последние пути для файлов'),
        )
        time.sleep(1)
        page.snack_bar.open = True
        page.update()


if __name__ == '__main__':
    ft.app(main)
