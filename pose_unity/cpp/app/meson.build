cmd = run_command('sh', '-c', 'echo $TAPPAS_WORKSPACE')
tappas_workspace = cmd.stdout().strip()

## Opencv Include Directories
#opencv_base_inc = include_directories('../../../../open_source/opencv/include/opencv4', is_system: true)
#opencv_inc = [opencv_base_inc]

################################################
# Pose tracking
################################################
pose_sources = [
'pose_estimation_tracking.cpp',
]

executable('pose_estimation_tracking',
    pose_sources,
    install_dir: tappas_workspace+'/apps/gstreamer/general/pose_unity',
    install: true,
    cpp_args : hailo_lib_args,
    include_directories: hailo_general_inc + cxxopts_inc, 
    dependencies : plugin_deps + [meta_dep] + [opencv_dep],
    gnu_symbol_visibility : 'default',
)

################################################
# Pose tracking MSPN
################################################
pose_sources = [
'pose_estimation_tracking_mspn.cpp',
]

executable('pose_estimation_tracking_mspn',
    pose_sources,
    install_dir: tappas_workspace+'/apps/gstreamer/general/pose_unity',
    install: true,
    cpp_args : hailo_lib_args,
    include_directories: hailo_general_inc + cxxopts_inc, 
    dependencies : plugin_deps + [meta_dep] + [opencv_dep],
    gnu_symbol_visibility : 'default',
)
