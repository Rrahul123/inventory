from django.db import models
import uuid   
import secrets
import string
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files import File
import os
from django.dispatch import receiver


class StockCategory(models.Model):
    id = models.AutoField(primary_key=True)
    category = models.CharField(max_length=30, unique=True)

    def __str__(self):
	    return self.category


def create_unique_id():
    res = ''.join(secrets.choice( string.digits) for i in range(13))
    return res


class Stock(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    barcode = models.ImageField(upload_to='barcode/', blank=True)
    category = models.ForeignKey('StockCategory', blank= True, null = True, on_delete=models.SET_NULL)
    code = models.CharField(max_length=15, unique=True, editable=False)
    sell_price = models.IntegerField(default=599)
    quantity = models.IntegerField(default=1)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
	    return self.name +'_'  +  self.code


    def save(self, *args, **kwargs):
        if not self.pk: 
            code = create_unique_id()
            unique = False
            while not unique:
                if not Stock.objects.filter(code=code).exists():
                    unique = True
                    self.code = code
                else:
                    print('clashed')
                    code = create_unique_id()
            EAN = barcode.get_barcode_class('ean13')
            ean = EAN(f'{code}', writer=ImageWriter())
            buffer = BytesIO()
            ean.write(buffer)
            self.barcode.save(f'{code}.png', File(buffer), save=False)
        super(Stock, self).save(*args, **kwargs)



@receiver(models.signals.post_delete, sender=Stock)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `MediaFile` object is deleted.
    """
    if instance.barcode:
        if os.path.isfile(instance.barcode.path):
            os.remove(instance.barcode.path)


@receiver(models.signals.pre_save, sender=Stock)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes old file from filesystem
    when corresponding `MediaFile` object is updated
    with new file.
    """
    if not instance.pk:
        return False
    try:
        old_file = Stock.objects.get(pk=instance.pk).barcode

    except Stock.DoesNotExist:
        return False

    new_file = instance.barcode
    if not old_file == new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)