# SPDX-FileCopyrightText: 2023 Vladislav Trofimenko <slashcooperlive@gmail.com>
#
# SPDX-License-Identifier: MIT

import glob
import io
import os

import time
from dataclasses import dataclass
import cv2
import flet as ft
import numpy as np
import platformdirs
from PIL import Image, ImageOps, ImageDraw
# from PIL import ImageDraw
from cairosvg import svg2png  # noqa


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
                input_path_field.value = e.path
            elif e.control.data == 'output':
                output_path_field.value = e.path
        page.update()

    def clean_error(e):
        e.control.error_text = None
        e.control.update()

    def scale_contour(cnt, scale):
        M = cv2.moments(cnt)
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])

        cnt_norm = cnt - [cx, cy]
        cnt_scaled = cnt_norm * scale
        cnt_scaled = cnt_scaled + [cx, cy]
        cnt_scaled = cnt_scaled.astype(np.int32)

        return cnt_scaled

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
            # mask.save('folder' + output_name)
            mask = np.asarray(mask)  # noqa
            scale_percent = 80.0
            radius = 0
            image_rst = np.asarray(image)  # noqa
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_L1)
            points3 = [pt[0] for ctr in contours for pt in ctr]
            points3 = np.array(points3).reshape((-1, 1, 2)).astype(np.int32)
            hull3 = cv2.convexHull(points3)
            result3 = cv2.drawContours(image_rst.copy(), [hull3], -1, (255, 255, 255), 1, cv2.LINE_AA)
            mask = cv2.cvtColor(result3, cv2.COLOR_BGR2GRAY)
            mask[mask != 0] = 255
            # (x, y), radius = cv2.minEnclosingCircle(hull3)
            # radius = round(radius)
            # print(radius)
            # center = (round(x), round(y))
            # cv2.circle(image_rst, center, radius, (0, 255, 0), 2)
            # cv2.imshow('result3', image_rst)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()
            while target_radius != radius:
                width = round(mask.shape[1] * scale_percent / 100)
                height = round(mask.shape[0] * scale_percent / 100)
                # width_image = round(mask.shape[1] * scale_percent / 100)
                # height_image = round(mask.shape[0] * scale_percent / 100)
                resized = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
                # resized_image = cv2.resize(image_rst, (width_image, height_image), interpolation=cv2.INTER_NEAREST)
                contours, _ = cv2.findContours(resized, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_L1)
                cnt = contours[0]
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                radius = round(radius)
                if radius < target_radius:
                    scale_percent += 0.5
                    continue
                elif radius > target_radius:
                    scale_percent -= 0.5
                    continue
                elif radius == target_radius:
                    center = (round(x), round(y))

                    # for contour in contours:
                    #     convexHull = cv2.convexHull(contour)
                    #     cv2.drawContours(resized_image, [convexHull], -1, (255, 0, 0), 2)
                    # cv2.imshow('Contours', resized_image)
                    # cv2.waitKey(0)
                    # cv2.destroyAllWindows()

                    # points3 = [pt[0] for ctr in contours for pt in ctr]
                    # points3 = np.array(points3).reshape((-1, 1, 2)).astype(np.int32)
                    # hull3 = cv2.convexHull(points3)
                    # result3 = cv2.drawContours(resized_image.copy(), [hull3], -1, (0, 255, 0), 1, cv2.LINE_AA)
                    # cv2.imshow('result3', result3)
                    # cv2.waitKey(0)
                    # cv2.destroyAllWindows()

                    # kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (10, 10))
                    # dilate = cv2.dilate(resized, kernel, iterations=5)
                    # cv2.imshow('Dilate', dilate)
                    # cv2.waitKey(0)
                    # cv2.destroyAllWindows()

                    # cv2.drawContours(resized_image, contours, -1, (0, 255, 0), 3)
                    # cv2.imshow('Contours', resized_image)
                    # cv2.waitKey(0)
                    # cv2.destroyAllWindows()
                    #
                    # cv2.circle(resized_image, center, radius, (0, 255, 0), 2)
                    # cv2.imshow('convex hull', resized_image)
                    # cv2.waitKey(0)
                    # cv2.destroyAllWindows()

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
            selected_paths.input = input_path_field.value
            selected_paths.output = output_path_field.value
            if selected_paths.input and selected_paths.output:
                start_button.disabled = False
            if not os.path.exists(cache_path):
                os.makedirs(cache_dir)
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
            on_click=lambda _: input_dialog.get_directory_path('Путь для чтения')
        ),
        on_change=clean_error,
    )
    output_path_field = ft.TextField(
        label='Путь для записи',
        width=float('inf'),
        height=48,
        text_size=12,
        suffix=ft.IconButton(
            icon=ft.icons.FOLDER,
            on_click=lambda _: output_dialog.get_directory_path('Путь для записи')
        ),
        on_change=clean_error,
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
        on_dismiss=close_dlg,
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
