import json
import boto3
import os
from urllib.parse import unquote_plus
import uuid
from datetime import datetime

# Initialize AWS clients
s3 = boto3.client('s3')
mediaconvert = boto3.client('mediaconvert', endpoint_url=os.environ['MEDIACONVERT_ENDPOINT'])
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Get environment variables
MEDIACONVERT_ROLE = os.environ['MEDIACONVERT_ROLE_ARN']
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
JOB_TABLE = os.environ.get('JOB_TABLE', 'VideoProcessingJobs')
SNS_TOPIC = os.environ.get('SNS_TOPIC_ARN')

# Video encoding presets
ENCODING_PRESETS = {
    'training-optimized': {
        'hls': [
            {
                'name': '360p',
                'width': 640,
                'height': 360,
                'bitrate': 800000,
                'maxBitrate': 1000000,
                'bufferSize': 1600000,
                'level': '3.0',
                'profile': 'MAIN'
            },
            {
                'name': '720p',
                'width': 1280,
                'height': 720,
                'bitrate': 2500000,
                'maxBitrate': 3000000,
                'bufferSize': 5000000,
                'level': '3.1',
                'profile': 'MAIN'
            },
            {
                'name': '1080p',
                'width': 1920,
                'height': 1080,
                'bitrate': 5000000,
                'maxBitrate': 6000000,
                'bufferSize': 10000000,
                'level': '4.0',
                'profile': 'HIGH'
            }
        ],
        'mp4': [
            {
                'name': 'download_720p',
                'width': 1280,
                'height': 720,
                'bitrate': 2000000,
                'profile': 'MAIN'
            }
        ]
    }
}

def lambda_handler(event, context):
    """
    Process uploaded training videos:
    1. Create multiple quality versions for adaptive streaming
    2. Generate thumbnails
    3. Extract metadata
    4. Update database
    """
    
    # Get S3 event details
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        # Skip if not a video file
        if not key.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
            continue
            
        print(f"Processing video: s3://{bucket}/{key}")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Extract metadata from key (expected format: uploads/courseId/moduleId/filename.mp4)
        try:
            parts = key.split('/')
            course_id = parts[1] if len(parts) > 1 else 'unknown'
            module_id = parts[2] if len(parts) > 2 else 'unknown'
            filename = parts[-1]
        except:
            course_id = 'unknown'
            module_id = 'unknown'
            filename = key.split('/')[-1]
        
        # Create output paths
        output_base = f"processed/{course_id}/{module_id}/{job_id}"
        
        # Save job to DynamoDB
        save_job_status(job_id, {
            'bucket': bucket,
            'input_key': key,
            'course_id': course_id,
            'module_id': module_id,
            'status': 'SUBMITTED',
            'created_at': datetime.utcnow().isoformat()
        })
        
        try:
            # Create MediaConvert job
            job = create_mediaconvert_job(
                bucket, 
                key, 
                output_base,
                job_id
            )
            
            # Update job status
            save_job_status(job_id, {
                'status': 'PROCESSING',
                'mediaconvert_job_id': job['Job']['Id']
            })
            
            # Send SNS notification
            if SNS_TOPIC:
                send_notification(
                    f"Video processing started",
                    f"Job {job_id} started for {filename} in course {course_id}"
                )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Video processing job created',
                    'jobId': job_id,
                    'mediaConvertJobId': job['Job']['Id']
                })
            }
            
        except Exception as e:
            print(f"Error creating MediaConvert job: {str(e)}")
            
            # Update job status
            save_job_status(job_id, {
                'status': 'FAILED',
                'error': str(e)
            })
            
            # Send error notification
            if SNS_TOPIC:
                send_notification(
                    f"Video processing failed",
                    f"Job {job_id} failed for {filename}: {str(e)}"
                )
            
            raise e

def create_mediaconvert_job(bucket, key, output_base, job_id):
    """Create MediaConvert job with HLS and MP4 outputs."""
    
    preset = ENCODING_PRESETS['training-optimized']
    
    job_settings = {
        'Role': MEDIACONVERT_ROLE,
        'UserMetadata': {
            'jobId': job_id,
            'courseId': output_base.split('/')[1],
            'moduleId': output_base.split('/')[2]
        },
        'Settings': {
            'Inputs': [{
                'FileInput': f's3://{bucket}/{key}',
                'VideoSelector': {
                    'ColorSpace': 'FOLLOW'
                },
                'AudioSelectors': {
                    'Audio Selector 1': {
                        'DefaultSelection': 'DEFAULT'
                    }
                },
                'TimecodeSource': 'ZEROBASED'
            }],
            'OutputGroups': []
        }
    }
    
    # Add HLS output group for adaptive streaming
    if 'hls' in preset:
        hls_group = create_hls_output_group(OUTPUT_BUCKET, output_base, preset['hls'])
        job_settings['Settings']['OutputGroups'].append(hls_group)
    
    # Add MP4 output group for downloads
    if 'mp4' in preset:
        mp4_group = create_mp4_output_group(OUTPUT_BUCKET, output_base, preset['mp4'])
        job_settings['Settings']['OutputGroups'].append(mp4_group)
    
    # Add thumbnail output group
    thumbnail_group = create_thumbnail_output_group(OUTPUT_BUCKET, output_base)
    job_settings['Settings']['OutputGroups'].append(thumbnail_group)
    
    # Create the job
    response = mediaconvert.create_job(**job_settings)
    
    return response

def create_hls_output_group(bucket, output_base, variants):
    """Create HLS output group configuration."""
    
    outputs = []
    
    for variant in variants:
        output = {
            'Preset': create_video_preset(variant),
            'NameModifier': variant['name'],
            'OutputSettings': {
                'HlsSettings': {
                    'AudioGroupId': 'audio',
                    'IFrameOnlyManifest': 'EXCLUDE'
                }
            }
        }
        outputs.append(output)
    
    # Add audio-only output for bandwidth optimization
    outputs.append({
        'Preset': create_audio_preset(),
        'NameModifier': 'audio',
        'OutputSettings': {
            'HlsSettings': {
                'AudioGroupId': 'audio',
                'AudioTrackType': 'AUDIO_ONLY_VARIANT_STREAM'
            }
        }
    })
    
    return {
        'Name': 'HLS',
        'OutputGroupSettings': {
            'Type': 'HLS_GROUP_SETTINGS',
            'HlsGroupSettings': {
                'Destination': f's3://{bucket}/{output_base}/hls/',
                'SegmentLength': 6,
                'MinSegmentLength': 0,
                'DirectoryStructure': 'SINGLE_DIRECTORY',
                'ManifestDurationFormat': 'INTEGER',
                'StreamInfResolution': 'INCLUDE',
                'ClientCache': 'ENABLED',
                'CaptionLanguageSetting': 'OMIT',
                'ManifestCompression': 'NONE',
                'CodecSpecification': 'RFC_4281',
                'OutputSelection': 'MANIFESTS_AND_SEGMENTS',
                'ProgramDateTime': 'EXCLUDE',
                'ProgramDateTimePeriod': 600,
                'TimedMetadataId3Frame': 'PRIV',
                'TimedMetadataId3Period': 10,
                'AudioOnlyContainer': 'AUTOMATIC',
                'SegmentControl': 'SEGMENTED_FILES'
            }
        },
        'Outputs': outputs
    }

def create_mp4_output_group(bucket, output_base, variants):
    """Create MP4 output group configuration."""
    
    outputs = []
    
    for variant in variants:
        output = {
            'Preset': create_video_preset(variant),
            'NameModifier': variant['name'],
            'ContainerSettings': {
                'Container': 'MP4',
                'Mp4Settings': {
                    'CslgAtom': 'INCLUDE',
                    'FreeSpaceBox': 'EXCLUDE',
                    'MoovPlacement': 'PROGRESSIVE_DOWNLOAD'
                }
            }
        }
        outputs.append(output)
    
    return {
        'Name': 'MP4',
        'OutputGroupSettings': {
            'Type': 'FILE_GROUP_SETTINGS',
            'FileGroupSettings': {
                'Destination': f's3://{bucket}/{output_base}/downloads/'
            }
        },
        'Outputs': outputs
    }

def create_thumbnail_output_group(bucket, output_base):
    """Create thumbnail output group configuration."""
    
    return {
        'Name': 'Thumbnails',
        'OutputGroupSettings': {
            'Type': 'FILE_GROUP_SETTINGS',
            'FileGroupSettings': {
                'Destination': f's3://{bucket}/{output_base}/thumbnails/'
            }
        },
        'Outputs': [{
            'ContainerSettings': {
                'Container': 'RAW'
            },
            'VideoDescription': {
                'Width': 1280,
                'Height': 720,
                'CodecSettings': {
                    'Codec': 'FRAME_CAPTURE',
                    'FrameCaptureSettings': {
                        'FramerateNumerator': 1,
                        'FramerateDenominator': 5,
                        'MaxCaptures': 10,
                        'Quality': 80
                    }
                }
            },
            'NameModifier': 'thumbnail'
        }]
    }

def create_video_preset(variant):
    """Create video encoding preset."""
    
    return {
        'VideoDescription': {
            'Width': variant['width'],
            'Height': variant['height'],
            'CodecSettings': {
                'Codec': 'H_264',
                'H264Settings': {
                    'RateControlMode': 'QVBR',
                    'QvbrSettings': {
                        'QvbrQualityLevel': 7,
                        'MaxAverageBitrate': variant.get('maxBitrate', variant['bitrate'])
                    },
                    'CodecProfile': variant.get('profile', 'MAIN'),
                    'CodecLevel': variant.get('level', 'AUTO'),
                    'InterlaceMode': 'PROGRESSIVE',
                    'ParControl': 'INITIALIZE_FROM_SOURCE',
                    'NumberReferenceFrames': 3,
                    'Syntax': 'DEFAULT',
                    'Softness': 0,
                    'GopSize': 90,
                    'GopBReference': 'DISABLED',
                    'GopSizeUnits': 'FRAMES',
                    'GopClosedCadence': 1,
                    'HrdBufferInitialFillPercentage': 90,
                    'HrdBufferSize': variant.get('bufferSize', variant['bitrate'] * 2),
                    'SlowPal': 'DISABLED',
                    'ParNumerator': 1,
                    'ParDenominator': 1,
                    'SpatialAdaptiveQuantization': 'ENABLED',
                    'TemporalAdaptiveQuantization': 'ENABLED',
                    'FlickerAdaptiveQuantization': 'DISABLED',
                    'EntropyEncoding': 'CABAC',
                    'FramerateControl': 'INITIALIZE_FROM_SOURCE',
                    'FramerateConversionAlgorithm': 'DUPLICATE_DROP',
                    'AdaptiveQuantization': 'HIGH',
                    'SceneChangeDetect': 'ENABLED',
                    'QualityTuningLevel': 'SINGLE_PASS_HQ'
                }
            },
            'AfdSignaling': 'NONE',
            'DropFrameTimecode': 'ENABLED',
            'RespondToAfd': 'NONE',
            'ColorMetadata': 'INSERT'
        },
        'AudioDescriptions': [{
            'CodecSettings': {
                'Codec': 'AAC',
                'AacSettings': {
                    'Bitrate': 128000,
                    'CodingMode': 'CODING_MODE_2_0',
                    'SampleRate': 48000,
                    'RawFormat': 'NONE',
                    'Specification': 'MPEG4',
                    'AudioDescriptionBroadcasterMix': 'NORMAL'
                }
            },
            'AudioTypeControl': 'FOLLOW_INPUT',
            'AudioSourceName': 'Audio Selector 1',
            'LanguageCodeControl': 'FOLLOW_INPUT'
        }]
    }

def create_audio_preset():
    """Create audio-only encoding preset."""
    
    return {
        'AudioDescriptions': [{
            'CodecSettings': {
                'Codec': 'AAC',
                'AacSettings': {
                    'Bitrate': 96000,
                    'CodingMode': 'CODING_MODE_2_0',
                    'SampleRate': 48000,
                    'RawFormat': 'NONE',
                    'Specification': 'MPEG4',
                    'AudioDescriptionBroadcasterMix': 'NORMAL'
                }
            },
            'AudioTypeControl': 'FOLLOW_INPUT',
            'AudioSourceName': 'Audio Selector 1',
            'LanguageCodeControl': 'FOLLOW_INPUT'
        }]
    }

def save_job_status(job_id, updates):
    """Save job status to DynamoDB."""
    
    table = dynamodb.Table(JOB_TABLE)
    
    # Build update expression
    update_expr = "SET "
    expr_values = {}
    
    for key, value in updates.items():
        update_expr += f"#{key} = :{key}, "
        expr_values[f":{key}"] = value
    
    update_expr = update_expr.rstrip(", ")
    update_expr += ", updated_at = :updated_at"
    expr_values[":updated_at"] = datetime.utcnow().isoformat()
    
    # Create attribute names to handle reserved words
    expr_names = {f"#{k}": k for k in updates.keys()}
    
    table.update_item(
        Key={'job_id': job_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values
    )

def send_notification(subject, message):
    """Send SNS notification."""
    
    if SNS_TOPIC:
        sns.publish(
            TopicArn=SNS_TOPIC,
            Subject=subject,
            Message=message
        )