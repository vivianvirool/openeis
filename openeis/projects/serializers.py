import csv
import posixpath

from rest_framework import serializers
from rest_framework.reverse import reverse

from .storage.csv import CSVFile
from . import models


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Project
        exclude = ('owner',)


# Split file creation from other file operations because the file should
# be unchangeable once it is uploaded and assigned to the user's # project.

class CreateFileSerializer(serializers.ModelSerializer):
    '''Serializer used to create/upload file.
    
    It ensures the file is associated with the appropriate project.
    '''
    class Meta:
        model = models.DataFile
        exclude = ('project',)

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

    def validate_file(self, attrs, source):
        # Only perform this validation when called from our add_file view.
        if self.project is None:
            return attrs
        file = attrs[source].file
        try:
            csv_file = CSVFile(file)
            cols = len(next(csv_file))
            for row in csv_file:
                if len(row) != cols:
                    raise csv.Error('Inconsistent number of columns')
        except csv.Error as e:
            raise serializers.ValidationError(str(e))
        file.seek(0)
        return attrs

    def restore_object(self, attrs, instance=None):
        #if self.project is not None:
        #    attrs['project'] = self.project
        #return super().restore_object(attrs, instance)
        obj = super().restore_object(attrs, instance)
        if self.project is not None:
            obj.project = self.project
        return obj


class FileSerializer(serializers.ModelSerializer):
    '''Serializer for file viewing/modification.

    Only the comments field of the file is updateable. If the request
    attribute is set, download_url will contain an absolute URL.
    '''
    download_url = serializers.CharField(source='pk', read_only=True)
    size = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = models.DataFile
        read_only_fields = ('project', 'file')

    def transform_file(self, obj, value):
        return posixpath.basename(value)

    def transform_download_url(self, obj, value):
        return reverse('datafile-download', kwargs={'pk': value},
                       request=getattr(self, 'request', None))

    def transform_size(self, obj, value):
        return obj.file.file.size


class MinimalUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = ('id', 'username', 'last_name', 'first_name')


class VerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AccountVerification
        fields = ('id', 'initiated', 'what')


class UserSerializer(serializers.ModelSerializer):
    verifications = VerificationSerializer(source='accountverification_set',
                                           many=True, read_only=True)

    class Meta:
        model = models.User
        fields = ('id', 'username', 'email', 'last_name', 'first_name',
                  'date_joined', 'last_login', 'groups', 'verifications')
        read_only_fields = ('username', 'last_login', 'date_joined', 'groups')


class CreateUserSerializer(UserSerializer):
    password = serializers.CharField(required=True, write_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('password',)
        read_only_fields = UserSerializer.Meta.read_only_fields[1:]

    def restore_object(self, attrs, instance=None):
        password = attrs.pop('password', None)
        instance = super().restore_object(attrs, instance)
        if password:
            instance.set_password(password)
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def restore_object(self, attrs, instance=None):
        return (attrs.get('old_password', instance and instance[0]),
                attrs.get('new_password', instance and instance[1]))


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(required=True, write_only=True)

    def restore_object(self, attrs, instance=None):
        return attrs.get('password', instance)


class ResetRequestSerializer(serializers.Serializer):
    username_or_email = serializers.CharField(required=True)

    def restore_object(self, attrs, instance=None):
        return attrs.get('username_or_email', instance)


class PasswordResetSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    code = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def restore_object(self, attrs, instance=None):
        return (attrs.get('username', instance and instance[0]),
                attrs.get('code', instance and instance[1]),
                attrs.get('password', instance and instance[2]))


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def restore_object(self, attrs, instance=None):
        return (attrs.get('username', instance and instance[0]),
                attrs.get('password', instance and instance[1]))


class SensorMapDefSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SensorMapDefinition
