import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit2, Trash2, Upload, Video, FileText, Package } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Select } from '@/components/ui/Select';
import { useAuth } from '@/hooks/useAuth';
import { TrainingService } from '@/services/api';
import { toast } from '@/hooks/useToast';

export default function ContentManagement() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('courses');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);

  // Check admin access
  if (!user?.roles?.includes('admin') && !user?.roles?.includes('training_manager')) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-500">您沒有權限訪問此頁面</p>
      </div>
    );
  }

  // Fetch courses
  const { data: courses, isLoading: coursesLoading } = useQuery({
    queryKey: ['admin-courses'],
    queryFn: () => TrainingService.getAllCourses({ includeInactive: true }),
  });

  // Fetch modules
  const { data: modules, isLoading: modulesLoading } = useQuery({
    queryKey: ['admin-modules'],
    queryFn: () => TrainingService.getAllModules({ includeInactive: true }),
  });

  // Create course mutation
  const createCourseMutation = useMutation({
    mutationFn: (data) => TrainingService.createCourse(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin-courses']);
      toast.success('課程建立成功');
      setIsCreateDialogOpen(false);
    },
    onError: (error) => {
      toast.error('建立課程失敗：' + error.message);
    },
  });

  // Update course mutation
  const updateCourseMutation = useMutation({
    mutationFn: ({ id, data }) => TrainingService.updateCourse(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin-courses']);
      toast.success('課程更新成功');
      setEditingItem(null);
    },
    onError: (error) => {
      toast.error('更新課程失敗：' + error.message);
    },
  });

  // Delete course mutation
  const deleteCourseMutation = useMutation({
    mutationFn: (id) => TrainingService.deleteCourse(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin-courses']);
      toast.success('課程刪除成功');
    },
    onError: (error) => {
      toast.error('刪除課程失敗：' + error.message);
    },
  });

  // Upload video mutation
  const uploadVideoMutation = useMutation({
    mutationFn: ({ moduleId, file }) => TrainingService.uploadVideo(moduleId, file),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin-modules']);
      toast.success('影片上傳成功，處理中...');
    },
    onError: (error) => {
      toast.error('上傳影片失敗：' + error.message);
    },
  });

  const handleCreateCourse = (formData) => {
    createCourseMutation.mutate({
      title_zh: formData.title_zh,
      title_en: formData.title_en,
      description_zh: formData.description_zh,
      description_en: formData.description_en,
      department: formData.department,
      difficulty: formData.difficulty,
      duration_hours: parseInt(formData.duration_hours),
      is_required: formData.is_required === 'true',
      category: formData.category,
      prerequisites: formData.prerequisites ? formData.prerequisites.split(',') : [],
      objectives: formData.objectives ? formData.objectives.split('\n') : [],
      tags: formData.tags ? formData.tags.split(',') : [],
    });
  };

  const handleUpdateCourse = (id, formData) => {
    updateCourseMutation.mutate({
      id,
      data: {
        title_zh: formData.title_zh,
        title_en: formData.title_en,
        description_zh: formData.description_zh,
        description_en: formData.description_en,
        department: formData.department,
        difficulty: formData.difficulty,
        duration_hours: parseInt(formData.duration_hours),
        is_required: formData.is_required === 'true',
        is_active: formData.is_active === 'true',
      },
    });
  };

  const handleDeleteCourse = (id, title) => {
    if (confirm(`確定要刪除課程「${title}」嗎？`)) {
      deleteCourseMutation.mutate(id);
    }
  };

  const handleVideoUpload = (moduleId, event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/webm'];
    if (!validTypes.includes(file.type)) {
      toast.error('請上傳有效的影片檔案 (MP4, MOV, AVI, MKV, WebM)');
      return;
    }

    // Validate file size (max 2GB)
    const maxSize = 2 * 1024 * 1024 * 1024; // 2GB
    if (file.size > maxSize) {
      toast.error('影片檔案大小不能超過 2GB');
      return;
    }

    uploadVideoMutation.mutate({ moduleId, file });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">內容管理</h1>
          <p className="mt-2 text-gray-600">管理培訓課程、模組和教材</p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger value="courses" className="flex items-center gap-2">
              <Package className="w-4 h-4" />
              課程管理
            </TabsTrigger>
            <TabsTrigger value="modules" className="flex items-center gap-2">
              <Video className="w-4 h-4" />
              模組管理
            </TabsTrigger>
            <TabsTrigger value="materials" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              教材管理
            </TabsTrigger>
          </TabsList>

          <TabsContent value="courses">
            <Card className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">課程列表</h2>
                <Button onClick={() => setIsCreateDialogOpen(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  新增課程
                </Button>
              </div>

              {coursesLoading ? (
                <div className="text-center py-8">載入中...</div>
              ) : (
                <div className="space-y-4">
                  {courses?.map((course) => (
                    <div
                      key={course.course_id}
                      className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg">{course.title_zh}</h3>
                          <p className="text-sm text-gray-500 mt-1">{course.title_en}</p>
                          <p className="text-gray-600 mt-2">{course.description_zh}</p>
                          <div className="flex gap-4 mt-3 text-sm text-gray-500">
                            <span>部門：{course.department}</span>
                            <span>難度：{course.difficulty}</span>
                            <span>時長：{course.duration_hours} 小時</span>
                            <span>狀態：{course.is_active ? '啟用' : '停用'}</span>
                          </div>
                        </div>
                        <div className="flex gap-2 ml-4">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditingItem(course)}
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteCourse(course.course_id, course.title_zh)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </TabsContent>

          <TabsContent value="modules">
            <Card className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">模組列表</h2>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  新增模組
                </Button>
              </div>

              {modulesLoading ? (
                <div className="text-center py-8">載入中...</div>
              ) : (
                <div className="space-y-4">
                  {modules?.map((module) => (
                    <div
                      key={module.module_id}
                      className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg">{module.title_zh}</h3>
                          <p className="text-sm text-gray-500 mt-1">
                            課程：{module.course?.title_zh}
                          </p>
                          <p className="text-gray-600 mt-2">{module.description_zh}</p>
                          <div className="flex gap-4 mt-3 text-sm text-gray-500">
                            <span>類型：{module.content_type}</span>
                            <span>時長：{module.duration_minutes} 分鐘</span>
                            <span>順序：{module.order_index}</span>
                          </div>
                        </div>
                        <div className="flex gap-2 ml-4">
                          <label className="cursor-pointer">
                            <input
                              type="file"
                              accept="video/*"
                              className="hidden"
                              onChange={(e) => handleVideoUpload(module.module_id, e)}
                            />
                            <Button variant="ghost" size="sm" asChild>
                              <span>
                                <Upload className="w-4 h-4" />
                              </span>
                            </Button>
                          </label>
                          <Button variant="ghost" size="sm">
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </TabsContent>

          <TabsContent value="materials">
            <Card className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">教材列表</h2>
                <Button>
                  <Upload className="w-4 h-4 mr-2" />
                  上傳教材
                </Button>
              </div>

              <div className="text-center py-8 text-gray-500">
                教材管理功能開發中...
              </div>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Create/Edit Course Dialog */}
        <Dialog
          open={isCreateDialogOpen || !!editingItem}
          onOpenChange={(open) => {
            if (!open) {
              setIsCreateDialogOpen(false);
              setEditingItem(null);
            }
          }}
        >
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingItem ? '編輯課程' : '新增課程'}
              </DialogTitle>
            </DialogHeader>
            <CourseForm
              course={editingItem}
              onSubmit={(data) => {
                if (editingItem) {
                  handleUpdateCourse(editingItem.course_id, data);
                } else {
                  handleCreateCourse(data);
                }
              }}
              onCancel={() => {
                setIsCreateDialogOpen(false);
                setEditingItem(null);
              }}
            />
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

function CourseForm({ course, onSubmit, onCancel }) {
  const [formData, setFormData] = useState({
    title_zh: course?.title_zh || '',
    title_en: course?.title_en || '',
    description_zh: course?.description_zh || '',
    description_en: course?.description_en || '',
    department: course?.department || 'all',
    difficulty: course?.difficulty || 'beginner',
    duration_hours: course?.duration_hours || '',
    is_required: course?.is_required ? 'true' : 'false',
    is_active: course?.is_active !== false ? 'true' : 'false',
    category: course?.category || 'general',
    prerequisites: course?.prerequisites?.join(', ') || '',
    objectives: course?.objectives?.join('\n') || '',
    tags: course?.tags?.join(', ') || '',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">課程名稱（中文）</label>
          <Input
            value={formData.title_zh}
            onChange={(e) => setFormData({ ...formData, title_zh: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">課程名稱（英文）</label>
          <Input
            value={formData.title_en}
            onChange={(e) => setFormData({ ...formData, title_en: e.target.value })}
            required
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">課程描述（中文）</label>
        <Textarea
          value={formData.description_zh}
          onChange={(e) => setFormData({ ...formData, description_zh: e.target.value })}
          rows={3}
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">課程描述（英文）</label>
        <Textarea
          value={formData.description_en}
          onChange={(e) => setFormData({ ...formData, description_en: e.target.value })}
          rows={3}
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">部門</label>
          <Select
            value={formData.department}
            onChange={(e) => setFormData({ ...formData, department: e.target.value })}
          >
            <option value="all">全體員工</option>
            <option value="office">辦公室</option>
            <option value="delivery">配送</option>
            <option value="management">管理</option>
          </Select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">難度</label>
          <Select
            value={formData.difficulty}
            onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
          >
            <option value="beginner">初級</option>
            <option value="intermediate">中級</option>
            <option value="advanced">進階</option>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">時長（小時）</label>
          <Input
            type="number"
            value={formData.duration_hours}
            onChange={(e) => setFormData({ ...formData, duration_hours: e.target.value })}
            min="1"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">是否必修</label>
          <Select
            value={formData.is_required}
            onChange={(e) => setFormData({ ...formData, is_required: e.target.value })}
          >
            <option value="true">是</option>
            <option value="false">否</option>
          </Select>
        </div>
        {course && (
          <div>
            <label className="block text-sm font-medium mb-1">狀態</label>
            <Select
              value={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.value })}
            >
              <option value="true">啟用</option>
              <option value="false">停用</option>
            </Select>
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">學習目標（每行一個）</label>
        <Textarea
          value={formData.objectives}
          onChange={(e) => setFormData({ ...formData, objectives: e.target.value })}
          rows={4}
          placeholder="完成本課程後，學員將能夠...&#10;理解...&#10;操作..."
        />
      </div>

      <div className="flex justify-end gap-3 mt-6">
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit">
          {course ? '更新' : '建立'}
        </Button>
      </div>
    </form>
  );
}